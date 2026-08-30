from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from process_phase4b_evidence import load_market, test_usdjpy

ROOT = Path(__file__).resolve().parents[1]
REQUESTS = ROOT / "phase4b_usdjpy_requests"
RESULTS = ROOT / "phase4b_usdjpy_results"
REPORTS = ROOT / "phase4b_usdjpy_reports"

def main() -> int:
    RESULTS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    failures = []
    for path in sorted(REQUESTS.glob("*.json")):
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
            rid = path.stem
            source_req_path = ROOT / meta["source_request"]
            req = json.loads(source_req_path.read_text(encoding="utf-8"))
            close, fx, vix = load_market(req)
            result = test_usdjpy(close, fx, vix, req)
            payload = {
                "request_id": rid,
                "status": "complete",
                "execution_role": "SAME_PREREG_CHECKPOINT_NOT_NEW_FAMILY",
                "source_request": meta["source_request"],
                "source_candidate_id": "JNU_V22_PHASE4B_USDJPY_1D",
                "research_spec_hash_note": "All research parameters are read directly from the existing Phase4B request.",
                "usdjpy": result,
                "promotion_status": "INFORMATION_STATE_SCREEN_ONLY",
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            (RESULTS / f"{rid}.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            lines = [
                f"# Phase4B USDJPY checkpoint — {rid}",
                "",
                "- Execution role: SAME_PREREG_CHECKPOINT_NOT_NEW_FAMILY",
                f"- OOS days: {result['oos_days']}",
                f"- Baseline MSE: {result['baseline_mse']:.10g}",
                f"- With USDJPY MSE: {result['with_usdjpy_mse']:.10g}",
                f"- MSE improvement: {result['mse_improvement']:.10g}",
                f"- Bootstrap P(improvement > 0): {result['bootstrap']['prob_positive']:.4f}",
                f"- Sign accuracy: {result['baseline_sign_accuracy']:.4f} -> {result['with_usdjpy_sign_accuracy']:.4f}",
                f"- Gate: **{'PASS' if result['pass_incremental_state'] else 'FAIL'}**",
                "",
                "This checkpoint executes the existing Phase4B USDJPY test independently from GDELT retrieval. It does not add a hypothesis or alter any parameter.",
                "",
            ]
            (REPORTS / f"{rid}.md").write_text("\n".join(lines), encoding="utf-8")
        except Exception as exc:
            failures.append((path.name, str(exc)))
    if failures:
        print(json.dumps({"failures": failures}, ensure_ascii=False))
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
