from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAIPEI = timezone(timedelta(hours=8))
JPX = ROOT / "scripts" / "fetch_jnu_exact_micro_quote_jpx_v1.py"
TV = ROOT / "scripts" / "fetch_jnu_exact_micro_quote_tradingview_v1.py"

STALE_PATTERNS = [
    re.compile(r"stale: age=([0-9.]+)s > ([0-9.]+)s; source=([^\s]+)"),
    re.compile(r"JPX quote stale: age=([0-9.]+)s > ([0-9.]+)s; source=([^\s]+)"),
]

def classify(name: str, script: Path, symbol: str, max_age: int, td: Path) -> dict:
    out = td / f"{name.lower()}_quote.json"
    cp = subprocess.run(
        [sys.executable, str(script), "--symbol", symbol, "--max-age-seconds", str(max_age), "--output", str(out)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    stderr = cp.stderr or ""
    stdout = cp.stdout or ""
    try:
        adapter_label=str(script.relative_to(ROOT).as_posix())
    except ValueError:
        adapter_label=str(script)
    rec = {
        "source": name,
        "adapter": adapter_label,
        "exit_code": cp.returncode,
        "status": None,
        "fresh": False,
        "quote": None,
        "stderr_tail": stderr[-3000:],
        "stdout_tail": stdout[-3000:],
    }
    if out.exists():
        try:
            rec["quote"] = json.loads(out.read_text(encoding="utf-8"))
        except Exception as exc:
            rec["quote_parse_error"] = str(exc)
    if cp.returncode == 0:
        if not isinstance(rec["quote"], dict):
            raise RuntimeError(f"{name} returned success without quote JSON")
        age = float(rec["quote"].get("freshness_age_seconds"))
        if age < 0 or age > max_age:
            raise RuntimeError(f"{name} success quote violates max-age gate: {age}")
        if rec["quote"].get("exact_product") is not True or rec["quote"].get("continuous_contract") is not False:
            raise RuntimeError(f"{name} success quote violates individual exact-Micro identity")
        rec["status"] = "FRESH_PASS"
        rec["fresh"] = True
        rec["observed_age_seconds"] = age
        rec["source_timestamp"] = rec["quote"].get("source_timestamp")
        return rec

    for pat in STALE_PATTERNS:
        m = pat.search(stderr)
        if m:
            rec["status"] = "SOURCE_REACHABLE_STALE"
            rec["observed_age_seconds"] = float(m.group(1))
            rec["maximum_age_seconds"] = float(m.group(2))
            rec["source_timestamp"] = m.group(3)
            return rec

    if "JPX exact Micro contract not found:" in stderr:
        rec["status"] = "CONTRACT_NOT_AVAILABLE_FROM_SOURCE"
        return rec
    rec["status"] = "ENGINEERING_OR_SOURCE_FAILURE"
    return rec

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="NK225MCU2026")
    ap.add_argument("--max-age-seconds", type=int, default=900)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.max_age_seconds != 900:
        raise RuntimeError("first-real source readiness probe is frozen at 900 seconds")

    started = datetime.now(TAIPEI)
    with tempfile.TemporaryDirectory(prefix="jnu_first_real_source_probe_") as td0:
        td = Path(td0)
        jpx = classify("JPX_OSE_OFFICIAL_EXACT_MICRO_A", JPX, args.symbol, args.max_age_seconds, td)
        tv = classify("TRADINGVIEW_OSE_EXACT_MICRO_B", TV, args.symbol, args.max_age_seconds, td)

    sources = [jpx, tv]
    fresh = [x for x in sources if x["fresh"]]
    failures = [x for x in sources if x["status"] == "ENGINEERING_OR_SOURCE_FAILURE"]
    unavailable = [x for x in sources if x["status"] == "CONTRACT_NOT_AVAILABLE_FROM_SOURCE"]
    stale = [x for x in sources if x["status"] == "SOURCE_REACHABLE_STALE"]
    if fresh:
        status = "FRESH_SOURCE_AVAILABLE"
        blocker = None
    elif failures:
        status = "FAIL_CLOSED_SOURCE_FAILURE"
        blocker = "INDIVIDUAL_EXACT_MICRO_SOURCE_OR_ENGINEERING_FAILURE"
    elif stale:
        status = "WAITING_FOR_FRESH_EXACT_MICRO"
        blocker = "INDIVIDUAL_EXACT_MICRO_REFERENCE_FRESHNESS"
    elif unavailable and len(unavailable) == len(sources):
        status = "FAIL_CLOSED_CONTRACT_NOT_DISCOVERABLE"
        blocker = "INDIVIDUAL_EXACT_MICRO_CONTRACT_NOT_DISCOVERABLE"
    else:
        status = "FAIL_CLOSED_SOURCE_CLASSIFICATION"
        blocker = "INDIVIDUAL_EXACT_MICRO_SOURCE_CLASSIFICATION_UNRESOLVED"

    result = {
        "version": "1.0",
        "status": status,
        "checked_at_taipei": started.isoformat(),
        "symbol": args.symbol,
        "maximum_reference_age_seconds": 900,
        "allowed_source_classes": [
            "JPX_OSE_OFFICIAL_EXACT_MICRO_A",
            "TRADINGVIEW_OSE_EXACT_MICRO_B",
        ],
        "continuous_contract_primary_prohibited": True,
        "fresh_source_count": len(fresh),
        "fresh_sources": [x["source"] for x in fresh],
        "blocker": blocker,
        "sources": sources,
        "formal_forecast_created": False,
        "real_ledger_modified": False,
        "directional_analysis_performed": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if failures:
        raise SystemExit(3)

if __name__ == "__main__":
    main()
