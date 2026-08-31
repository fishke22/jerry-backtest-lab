from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import process_jnu_news_language_source_g1 as g1
import process_jnu_news_language_source_g1_final as g1final
from process_phase4b_evidence import CACHE

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "news_language_g1_requests" / "jnu_news_language_source_g1_v1.json"
RESULTS = ROOT / "news_language_g1_results"
REPORTS = ROOT / "news_language_g1_reports"
DIAG = ROOT / "workflow_diagnostics"


def expected_cache(req: dict) -> tuple[bool, list[dict]]:
    start_day = pd.Timestamp(req["date_from"]).normalize()
    end_day = pd.Timestamp(req["date_to"]).normalize()
    start = start_day.strftime("%Y%m%d000000")
    end = (end_day + pd.Timedelta(days=1)).strftime("%Y%m%d000000")
    missing = []
    for cell in req["news"]["categories"]:
        for mode in ("TimelineTone", "TimelineVol"):
            for i, (a, b) in enumerate(g1.quarter_windows(start, end), start=1):
                quarter = CACHE / f"g1_{cell}_{mode.lower()}_q{i}_{a[:8]}_{b[:8]}.json"
                if quarter.exists():
                    continue
                for j, (sa, sb, _) in enumerate(g1final._direct_windows(a, b), start=1):
                    p = CACHE / f"g1_{cell}_{mode.lower()}_q{i}_{a[:8]}_{b[:8]}_D{j}_{sa[:8]}_{sb[:8]}.json"
                    if not p.exists():
                        missing.append({
                            "cell": cell, "mode": mode, "quarter": i, "chunk": j,
                            "start": sa, "end": sb, "cache": p.name,
                        })
    return len(missing) == 0, missing


def write_inconclusive(req: dict, missing: list[dict]) -> None:
    RESULTS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    DIAG.mkdir(exist_ok=True)
    rid = req["request_id"]
    result = {
        "request_id": rid,
        "candidate_id": "NEWS_STATE_LANGUAGE_SOURCE_G1",
        "status": "complete",
        "promotion_status": "DATA_INCONCLUSIVE",
        "disposition": "DATA_INCONCLUSIVE",
        "reason": "FINAL_ACQUISITION_BUDGET_EXHAUSTED_INCOMPLETE_FOUR_CELL_PANEL",
        "logical_attempts_used": 3,
        "data_integrity_revision": "G1_DI1",
        "statistical_evaluation_performed": False,
        "directional_trading_status": "PROHIBITED_G1",
        "missing_cache_count": len(missing),
        "missing_cache_examples": missing[:50],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (RESULTS / f"{rid}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = "\n".join([
        f"# JNU News Language/Source G1 — {rid}", "",
        "- Status: **DATA_INCONCLUSIVE**",
        "- Reason: final preregistered acquisition budget exhausted before a complete four-cell panel was available.",
        "- Statistical PASS/FAIL interpretation: **NOT PERFORMED**",
        "- Directional trading interpretation: **PROHIBITED**",
        f"- Missing cache windows: {len(missing)}", "",
        "No query, language cell, date range, half-life, OOS rule, bootstrap setting, Holm threshold, or pass threshold was changed.", "",
    ])
    (REPORTS / f"{rid}.md").write_text(report, encoding="utf-8")
    (DIAG / "g1_attempt3_terminal_completeness.json").write_text(
        json.dumps({"complete": False, "missing_count": len(missing), "missing": missing}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    req = json.loads(REQUEST.read_text(encoding="utf-8"))
    complete, missing = expected_cache(req)
    DIAG.mkdir(exist_ok=True)
    (DIAG / "g1_attempt3_terminal_completeness.json").write_text(
        json.dumps({"complete": complete, "missing_count": len(missing), "missing": missing}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not complete:
        write_inconclusive(req, missing)
        print(f"G1_ATTEMPT3_DATA_INCONCLUSIVE missing={len(missing)}")
        return 0

    # Complete-cache gate passed. Monkey-patched final loader can now only hit
    # already-present quarter/direct caches; no network acquisition is required.
    g1.gdelt_quarter_timeline = g1final.gdelt_final_timeline
    rc = g1.main()
    print(f"G1_ATTEMPT3_OFFLINE_EVALUATION_COMPLETE rc={rc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
