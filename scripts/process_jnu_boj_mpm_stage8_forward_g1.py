from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "config" / "jnu_boj_mpm_stage8_forward_g1_prereg.json"
DEFAULT_STAGE_B = ROOT / "event_volatility_results" / "jnu_boj_mpm_exact_jnu_micro_stage_b_g1.json"
DEFAULT_PANEL = ROOT / "cloud_data" / "derived" / "jnu_boj_mpm_micro_event_volatility_g1.csv"
DEFAULT_MANIFEST = ROOT / "cloud_data" / "manifests" / "jnu_boj_mpm_micro_event_volatility_g1_manifest.json"
DEFAULT_RESULT = ROOT / "event_volatility_results" / "jnu_boj_mpm_stage8_forward_g1.json"
DEFAULT_REPORT = ROOT / "event_volatility_reports" / "jnu_boj_mpm_stage8_forward_g1.md"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def bootstrap_mean(values: list[float], samples: int, seed: int) -> dict:
    rng = random.Random(seed)
    n = len(values)
    means: list[float] = []
    for _ in range(samples):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    ordered = sorted(means)
    lo = ordered[max(0, int(0.025 * samples) - 1)]
    hi = ordered[min(samples - 1, int(0.975 * samples))]
    return {
        "n": n,
        "mean": sum(values) / n,
        "prob_mean_positive": sum(x > 0 for x in means) / samples,
        "ci95": [lo, hi],
    }


def write_result(result: dict, output: Path, report: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if result["status"] == "STAGE8_FORWARD_EVENT_HOLDOUT_PENDING_INSUFFICIENT_NEW_EVENTS":
        text = (
            "# JNU BOJ MPM Stage8 Forward Event Holdout G1\n\n"
            f"- Status: **{result['status']}**\n"
            f"- New eligible events available: **{result['available_new_events']} / {result['required_new_events']}**\n"
            f"- Remaining events: **{result['remaining_new_events']}**\n"
            "- Partial event-effect performance: **PROHIBITED / NOT COMPUTED**\n"
        )
    else:
        m = result["holdout_metrics"]
        text = (
            "# JNU BOJ MPM Stage8 Forward Event Holdout G1\n\n"
            f"- Status: **{result['status']}**\n"
            f"- Holdout events: **{result['holdout_events']}**\n"
            f"- Mean primary effect: **{m['mean_primary_effect']:.12g}**\n"
            f"- Median primary effect: **{m['median_primary_effect']:.12g}**\n"
            f"- Bootstrap P(mean>0): **{m['bootstrap']['prob_mean_positive']}**\n"
            "- Role remains event/risk-state only; no directional-alpha interpretation.\n"
        )
    report.write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    ap.add_argument("--stage-b", type=Path, default=DEFAULT_STAGE_B)
    ap.add_argument("--panel", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--output", type=Path, default=DEFAULT_RESULT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    prereg = json.loads(args.prereg.read_text(encoding="utf-8"))
    stage_b = json.loads(args.stage_b.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))

    if stage_b.get("status") != "TRUE_JNU_MICRO_BOJ_EVENT_VOL_STAGE_B_PASS":
        raise RuntimeError("fail closed: Stage B PASS prerequisite not satisfied")
    if manifest.get("raw_data_cloud_uploaded") is not False:
        raise RuntimeError("fail closed: raw_data_cloud_uploaded must be false")
    if manifest.get("critical_data_quality_issues") != []:
        raise RuntimeError("fail closed: unresolved critical data-quality issues")
    if manifest.get("derived_output_hash") != sha256_file(args.panel):
        raise RuntimeError("fail closed: derived panel hash mismatch")

    with args.panel.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise RuntimeError("fail closed: empty event panel")

    required_cols = {
        "event_date", "baseline_rv_1m", "event_rv_1m",
        "log_event_to_baseline_rv_ratio", "baseline_return_count", "event_return_count",
    }
    if not required_cols.issubset(rows[0]):
        raise RuntimeError(f"fail closed: missing columns {sorted(required_cols - set(rows[0]))}")

    cutoff = prereg["source"]["pre_holdout_cutoff"]
    eligible: list[dict] = []
    for row in rows:
        if row["event_date"] <= cutoff:
            continue
        if int(float(row["baseline_return_count"])) != 30 or int(float(row["event_return_count"])) != 30:
            raise RuntimeError(f"fail closed: non-30-return forward event {row['event_date']}")
        effect = float(row["log_event_to_baseline_rv_ratio"])
        if not math.isfinite(effect):
            raise RuntimeError(f"fail closed: non-finite effect {row['event_date']}")
        eligible.append({"event_date": row["event_date"], "effect": effect})
    eligible.sort(key=lambda x: x["event_date"])

    required = int(prereg["holdout"]["event_count"])
    base = {
        "candidate_id": prereg["candidate_id"],
        "status": None,
        "prereg_sha256": sha256_file(args.prereg),
        "panel_sha256": sha256_file(args.panel),
        "manifest_sha256": sha256_file(args.manifest),
        "pre_holdout_cutoff": cutoff,
        "available_new_events": len(eligible),
        "required_new_events": required,
        "raw_data_cloud_uploaded": False,
        "role": "EVENT_RISK_STATE_ONLY_NOT_DIRECTIONAL_ALPHA",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    if len(eligible) < required:
        result = {
            **base,
            "status": "STAGE8_FORWARD_EVENT_HOLDOUT_PENDING_INSUFFICIENT_NEW_EVENTS",
            "remaining_new_events": required - len(eligible),
            "partial_holdout_performance_computed": False,
            "holdout_metrics_revealed": False,
        }
        write_result(result, args.output, args.report)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    holdout = eligible[:required]
    values = [x["effect"] for x in holdout]
    bcfg = prereg["evaluation"]["bootstrap"]
    boot = bootstrap_mean(values, int(bcfg["samples"]), int(bcfg["seed"]))
    mean_effect = statistics.fmean(values)
    median_effect = statistics.median(values)
    checks = {
        "exactly_8_events": len(values) == required,
        "mean_primary_effect_positive": mean_effect > 0,
        "median_primary_effect_positive": median_effect > 0,
        "bootstrap_prob_mean_positive_ge_0_95": boot["prob_mean_positive"] >= 0.95,
        "zero_critical_dq": True,
    }
    passed = all(checks.values())
    status = "STAGE8_FORWARD_EVENT_HOLDOUT_PASS" if passed else "STAGE8_FORWARD_EVENT_HOLDOUT_FAIL_CURRENT_SPEC"
    result = {
        **base,
        "status": status,
        "holdout_events": len(values),
        "holdout_from": holdout[0]["event_date"],
        "holdout_to": holdout[-1]["event_date"],
        "partial_holdout_performance_computed": False,
        "holdout_metrics_revealed": True,
        "checks": checks,
        "holdout_metrics": {
            "mean_primary_effect": mean_effect,
            "median_primary_effect": median_effect,
            "bootstrap": boot,
        },
        "next_rule": (
            "Proceed to Stage9 role-consistent validation review only; no directional promotion."
            if passed
            else "Terminal fail current Stage8 event-state spec; no event subset/window rescue."
        ),
    }
    write_result(result, args.output, args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
