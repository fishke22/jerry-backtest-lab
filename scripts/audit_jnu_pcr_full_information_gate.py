from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit(panel: dict, prereg: dict) -> dict:
    if panel.get("directional_return_outcomes_used") is not False:
        raise RuntimeError("directional-return contamination")
    if panel.get("formal_directional_family_opened") is not False:
        raise RuntimeError("formal-family contamination")
    if panel.get("alpha_evidence") is not False:
        raise RuntimeError("alpha-evidence contamination")

    gate = prereg["data_feasibility_gate"]
    months = sorted(panel["months"], key=lambda x: x["month"])
    names = [m["month"] for m in months]
    if len(names) != len(set(names)):
        raise RuntimeError("duplicate months")

    archive_complete = [m for m in months if m["status"] != "ARCHIVE_INCOMPLETE"]
    archive_incomplete = [m["month"] for m in months if m["status"] == "ARCHIVE_INCOMPLETE"]
    parser_errors = [m["month"] for m in months if m["status"] == "PARSER_OR_SOURCE_ERROR"]
    defined = [m for m in months if m["status"] == "PCR_DEFINED"]
    recent36 = archive_complete[-36:]
    recent_defined = [m for m in recent36 if m["status"] == "PCR_DEFINED"]

    checks = {
        "manifest_month_count_match": len(months) == gate["expected_manifest_months"],
        "archive_complete_count_match": len(archive_complete) == gate["expected_archive_complete_months"],
        "known_archive_incomplete_months_match": archive_incomplete == gate["known_archive_incomplete_months"],
        "zero_unexpected_parser_or_source_errors": len(parser_errors) == gate["unexpected_parser_or_source_errors_allowed"],
        "minimum_total_defined_months": len(defined) >= gate["minimum_pcr_defined_months"],
        "minimum_total_defined_fraction": (
            len(defined) / len(archive_complete)
        ) >= gate["minimum_total_defined_fraction_of_archive_complete"],
        "minimum_recent_defined_months": len(recent_defined) >= gate["minimum_recent_defined_months"],
        "minimum_recent_defined_fraction": (
            len(recent_defined) / len(recent36)
        ) >= gate["minimum_recent_defined_fraction"],
    }
    passed = all(checks.values())
    expected_status = (
        prereg["classification"]["pass"]
        if passed
        else prereg["classification"]["fail_or_inconclusive"]
    )
    checks["panel_status_matches_recomputed_gate"] = panel.get("status") == expected_status
    checks["panel_pass_flag_matches_recomputed_gate"] = panel.get("data_feasibility_pass") is passed

    return {
        "candidate_id": prereg["candidate_id"],
        "independent_gate_pass": passed,
        "expected_status": expected_status,
        "all_integrity_checks_pass": all(checks.values()),
        "checks": checks,
        "metrics": {
            "months_total": len(months),
            "archive_complete_months": len(archive_complete),
            "pcr_defined_months": len(defined),
            "parser_or_source_error_months": len(parser_errors),
            "defined_fraction_of_archive_complete": len(defined) / len(archive_complete),
            "recent36_defined_months": len(recent_defined),
            "recent36_defined_fraction": len(recent_defined) / len(recent36),
        },
        "archive_incomplete_months": archive_incomplete,
        "parser_or_source_error_months": parser_errors,
        "directional_return_outcomes_used": False,
        "formal_directional_family_opened": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", required=True, type=Path)
    parser.add_argument(
        "--prereg",
        type=Path,
        default=Path("config/jnu_pcr_full_information_panel_prereg_v1.json"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = audit(load_json(args.panel), load_json(args.prereg))
    result["panel_sha256"] = sha256_file(args.panel)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if not result["all_integrity_checks_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
