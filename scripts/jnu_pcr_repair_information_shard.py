from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

TARGET_MONTH = "2023-02"
SOURCE_YEAR_RANGE = [2022, 2026]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-shard", required=True, type=Path)
    ap.add_argument("--replacement-panel", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    source = load(args.source_shard)
    repl = load(args.replacement_panel)
    for name, panel in (("source", source), ("replacement", repl)):
        if panel.get("directional_return_outcomes_used") is not False:
            raise RuntimeError(f"{name}: directional contamination")
        if panel.get("formal_directional_family_opened") is not False:
            raise RuntimeError(f"{name}: formal family contamination")

    if source.get("year_range") != SOURCE_YEAR_RANGE:
        raise RuntimeError(f"unexpected source year range: {source.get('year_range')}")
    if len(source.get("months", [])) != 56:
        raise RuntimeError("source shard must contain exactly 56 months")

    parser_errors = [m for m in source["months"] if m.get("status") == "PARSER_OR_SOURCE_ERROR"]
    if len(parser_errors) != 1 or parser_errors[0].get("month") != TARGET_MONTH:
        raise RuntimeError(f"unexpected parser-error set: {[m.get('month') for m in parser_errors]}")
    if "reference Nikkei close not parsed" not in parser_errors[0].get("error", ""):
        raise RuntimeError("source error is not the frozen engineering incident")

    if len(repl.get("months", [])) != 1:
        raise RuntimeError("replacement panel must contain exactly one month")
    replacement = repl["months"][0]
    if replacement.get("month") != TARGET_MONTH or replacement.get("status") != "PCR_DEFINED":
        raise RuntimeError("replacement month is not repaired PCR_DEFINED 2023-02")
    if len(replacement.get("days", [])) != 5:
        raise RuntimeError("replacement month must contain five required days")
    if any("error" in d for d in replacement["days"]):
        raise RuntimeError("replacement month still contains day errors")
    repaired = copy.deepcopy(source)
    before = {m["month"]: canonical(m) for m in source["months"]}
    repaired["months"] = [
        copy.deepcopy(replacement) if m["month"] == TARGET_MONTH else m
        for m in repaired["months"]
    ]
    after = {m["month"]: canonical(m) for m in repaired["months"]}
    changed = [month for month in before if before[month] != after[month]]
    if changed != [TARGET_MONTH]:
        raise RuntimeError(f"unexpected changed months: {changed}")

    counts: dict[str, int] = {}
    for month in repaired["months"]:
        counts[month["status"]] = counts.get(month["status"], 0) + 1
    repaired["status_counts"] = counts
    repaired["engineering_recovery"] = {
        "target_month": TARGET_MONTH,
        "changed_months": changed,
        "source_shard_sha256": sha256(args.source_shard),
        "replacement_panel_sha256": sha256(args.replacement_panel),
        "research_rule_changed": False,
        "directional_return_outcomes_used": False,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(repaired, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PCR_INFORMATION_SHARD_ENGINEERING_RECOVERY_PASS",
        "changed_months": changed,
        "status_counts": counts,
        "output_sha256": sha256(args.output),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
