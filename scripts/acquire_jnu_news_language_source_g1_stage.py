from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import process_jnu_news_language_source_g1 as g1
from process_jnu_news_language_source_g1_final import _direct_windows
from process_phase4b_evidence import CACHE, _gdelt_timeline_adaptive

ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "news_language_g1_requests" / "jnu_news_language_source_g1_v1.json"
DIAG = ROOT / "workflow_diagnostics"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    req = json.loads(REQUEST.read_text(encoding="utf-8"))
    cell = os.environ["G1_CELL"]
    mode = os.environ["G1_MODE"]
    budget = int(os.environ.get("G1_STAGE_BUDGET_SECONDS", "2400"))
    reserve = int(os.environ.get("G1_STAGE_RESERVE_SECONDS", "150"))
    categories = req["news"]["categories"]
    if cell not in categories:
        raise ValueError(f"unknown G1 cell: {cell}")
    if mode not in {"TimelineTone", "TimelineVol"}:
        raise ValueError(f"invalid G1 mode: {mode}")

    start_day = pd.Timestamp(req["date_from"]).normalize()
    end_day = pd.Timestamp(req["date_to"]).normalize()
    start = start_day.strftime("%Y%m%d000000")
    end = (end_day + pd.Timedelta(days=1)).strftime("%Y%m%d000000")
    query = categories[cell]["query"]
    force = bool(req.get("force_refresh", False))
    t0 = time.monotonic()
    rows = []
    complete = True

    CACHE.mkdir(parents=True, exist_ok=True)
    DIAG.mkdir(parents=True, exist_ok=True)

    for i, (a, b) in enumerate(g1.quarter_windows(start, end), start=1):
        quarter_cache = f"g1_{cell}_{mode.lower()}_q{i}_{a[:8]}_{b[:8]}.json"
        quarter_path = CACHE / quarter_cache
        if quarter_path.exists() and not force:
            rows.append({"quarter": i, "start": a, "end": b, "status": "COMPLETE_QUARTER_CACHE"})
            continue

        q_complete = True
        for j, (sa, sb, _) in enumerate(_direct_windows(a, b), start=1):
            cache = f"g1_{cell}_{mode.lower()}_q{i}_{a[:8]}_{b[:8]}_D{j}_{sa[:8]}_{sb[:8]}.json"
            cache_path = CACHE / cache
            if cache_path.exists() and not force:
                rows.append({"quarter": i, "chunk": j, "start": sa, "end": sb, "status": "CACHE_HIT"})
                continue

            elapsed = time.monotonic() - t0
            if elapsed >= max(0, budget - reserve):
                rows.append({"quarter": i, "chunk": j, "start": sa, "end": sb, "status": "DEFERRED_STAGE_DEADLINE"})
                q_complete = False
                complete = False
                break

            try:
                _gdelt_timeline_adaptive(query, mode, sa, sb, cache, force)
                rows.append({"quarter": i, "chunk": j, "start": sa, "end": sb, "status": "ACQUIRED"})
            except Exception as exc:
                rows.append({
                    "quarter": i,
                    "chunk": j,
                    "start": sa,
                    "end": sb,
                    "status": "SOURCE_OR_NETWORK_FAILURE",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                })
                q_complete = False
                complete = False
                break

        if not q_complete:
            break

    payload = {
        "role": "G1_FINAL_ATTEMPT_ACQUISITION_STAGE_ONLY_NO_MODEL",
        "logical_attempt": int(req.get("execution", {}).get("logical_attempt", 3)),
        "cell": cell,
        "mode": mode,
        "started_at_utc": now_utc(),
        "elapsed_seconds": round(time.monotonic() - t0, 3),
        "stage_complete": bool(complete),
        "research_parameter_change": False,
        "rows": rows,
    }
    out = DIAG / f"g1_attempt3_acquire_{cell}_{mode.lower()}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ["role", "logical_attempt", "cell", "mode", "elapsed_seconds", "stage_complete"]}, ensure_ascii=False))
    # Acquisition incompleteness is a data outcome, not a CI/code failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
