from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAR_PREREG = ROOT / "config" / "jnu_har_rsv_jnu_micro_stage8_forward_g1_prereg.json"
HAR_PANEL = ROOT / "cloud_data" / "derived" / "jnu_225labo_micro_daily_rvrsv_v1.csv"
HAR_MANIFEST = ROOT / "cloud_data" / "manifests" / "jnu_225labo_micro_daily_rvrsv_v1_manifest.json"
BOJ_PREREG = ROOT / "config" / "jnu_boj_mpm_stage8_forward_g1_prereg.json"
BOJ_PANEL = ROOT / "cloud_data" / "derived" / "jnu_boj_mpm_micro_event_volatility_g1.csv"
BOJ_MANIFEST = ROOT / "cloud_data" / "manifests" / "jnu_boj_mpm_micro_event_volatility_g1_manifest.json"
DEFAULT_OUTPUT = ROOT / "stage8_readiness" / "jnu_stage8_readiness_v1.json"
DEFAULT_REPORT = ROOT / "stage8_readiness" / "jnu_stage8_readiness_v1.md"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def har_readiness() -> dict:
    prereg = load_json(HAR_PREREG)
    manifest = load_json(HAR_MANIFEST)
    if manifest.get("raw_data_cloud_uploaded") is not False:
        raise RuntimeError("HAR fail closed: raw_data_cloud_uploaded must be false")
    if manifest.get("critical_data_quality_issues") != []:
        raise RuntimeError("HAR fail closed: unresolved critical DQ issues")
    panel_hash = sha256_file(HAR_PANEL)
    if manifest.get("derived_output_hash") != panel_hash:
        raise RuntimeError("HAR fail closed: derived panel hash mismatch")

    cutoff = prereg["source"]["pre_holdout_cutoff"]
    required = int(prereg["holdout"]["length_trading_days"])
    min_returns = int(prereg["frozen_models"]["min_5m_returns_per_day"])
    dates: list[str] = []
    invalid_after_cutoff: list[str] = []

    with HAR_PANEL.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        required_cols = {"trading_date", "n_5m_returns"}
        if not required_cols.issubset(reader.fieldnames or []):
            raise RuntimeError(f"HAR fail closed: missing readiness columns {sorted(required_cols - set(reader.fieldnames or []))}")
        for row in reader:
            date = row["trading_date"]
            if date <= cutoff:
                continue
            try:
                nret = int(float(row["n_5m_returns"]))
            except Exception:
                invalid_after_cutoff.append(date)
                continue
            if nret < min_returns:
                invalid_after_cutoff.append(date)
                continue
            dates.append(date)

    dates = sorted(set(dates))
    if invalid_after_cutoff:
        raise RuntimeError(f"HAR fail closed: post-cutoff rows fail minimum-return integrity on {invalid_after_cutoff[:10]}")

    available = len(dates)
    status = "READY_TO_RUN_STAGE8" if available >= required else "PENDING_NEW_DATA"
    return {
        "candidate_id": prereg["candidate_id"],
        "status": status,
        "pre_holdout_cutoff": cutoff,
        "required_new_days": required,
        "available_new_days": available,
        "remaining_new_days": max(0, required - available),
        "first_new_date": dates[0] if dates else None,
        "last_new_date": dates[-1] if dates else None,
        "panel_sha256": panel_hash,
        "manifest_sha256": sha256_file(HAR_MANIFEST),
        "performance_metrics_computed": False,
        "performance_columns_read": False,
    }


def boj_readiness() -> dict:
    prereg = load_json(BOJ_PREREG)
    manifest = load_json(BOJ_MANIFEST)
    if manifest.get("raw_data_cloud_uploaded") is not False:
        raise RuntimeError("BOJ fail closed: raw_data_cloud_uploaded must be false")
    if manifest.get("critical_data_quality_issues") != []:
        raise RuntimeError("BOJ fail closed: unresolved critical DQ issues")
    panel_hash = sha256_file(BOJ_PANEL)
    if manifest.get("derived_output_hash") != panel_hash:
        raise RuntimeError("BOJ fail closed: derived panel hash mismatch")

    cutoff = prereg["source"]["pre_holdout_cutoff"]
    required = int(prereg["holdout"]["event_count"])
    dates: list[str] = []
    invalid_after_cutoff: list[str] = []

    with BOJ_PANEL.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        required_cols = {"event_date", "baseline_return_count", "event_return_count"}
        if not required_cols.issubset(reader.fieldnames or []):
            raise RuntimeError(f"BOJ fail closed: missing readiness columns {sorted(required_cols - set(reader.fieldnames or []))}")
        for row in reader:
            date = row["event_date"]
            if date <= cutoff:
                continue
            try:
                nb = int(float(row["baseline_return_count"]))
                ne = int(float(row["event_return_count"]))
            except Exception:
                invalid_after_cutoff.append(date)
                continue
            if nb != 30 or ne != 30:
                invalid_after_cutoff.append(date)
                continue
            dates.append(date)

    dates = sorted(set(dates))
    if invalid_after_cutoff:
        raise RuntimeError(f"BOJ fail closed: post-cutoff event window integrity failed on {invalid_after_cutoff[:10]}")

    available = len(dates)
    status = "READY_TO_RUN_STAGE8" if available >= required else "PENDING_NEW_EVENTS"
    return {
        "candidate_id": prereg["candidate_id"],
        "status": status,
        "pre_holdout_cutoff": cutoff,
        "required_new_events": required,
        "available_new_events": available,
        "remaining_new_events": max(0, required - available),
        "first_new_event": dates[0] if dates else None,
        "last_new_event": dates[-1] if dates else None,
        "panel_sha256": panel_hash,
        "manifest_sha256": sha256_file(BOJ_MANIFEST),
        "performance_metrics_computed": False,
        "event_effect_columns_read": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    har = har_readiness()
    boj = boj_readiness()
    overall = "READY_FOR_AT_LEAST_ONE_STAGE8" if (
        har["status"] == "READY_TO_RUN_STAGE8" or boj["status"] == "READY_TO_RUN_STAGE8"
    ) else "STAGE8_DATA_ACCUMULATION_PENDING"
    result = {
        "version": "1.0",
        "status": overall,
        "HAR_RSV": har,
        "BOJ_MPM": boj,
        "performance_metrics_computed": False,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# JNU Stage8 Readiness Gate v1",
        "",
        f"- Overall: **{overall}**",
        f"- HAR-RSV: **{har['available_new_days']} / {har['required_new_days']}** new exact-JNU trading days; {har['status']}",
        f"- BOJ MPM: **{boj['available_new_events']} / {boj['required_new_events']}** new eligible policy events; {boj['status']}",
        "- Performance/effect metrics: **NOT COMPUTED / NOT READ**",
        "",
        "This gate is readiness-only. It cannot promote a module and cannot reveal partial Stage8 performance.",
        "",
    ]
    args.report.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
