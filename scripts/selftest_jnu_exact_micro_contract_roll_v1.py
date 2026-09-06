from __future__ import annotations

import importlib.util
import json
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MODPATH=ROOT/"scripts"/"resolve_jnu_exact_micro_contract_v1.py"
spec=importlib.util.spec_from_file_location("roll_mod",MODPATH)
m=importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(m)

def at(s:str):
    return datetime.fromisoformat(s)

def main()->None:
    cal=m.load_calendar()
    cases=[
      ("2026-09-10T08:50:00+09:00","NK225MCU2026"),
      ("2026-09-10T15:59:59+09:00","NK225MCU2026"),
      ("2026-09-10T17:05:00+09:00","NK225MCV2026"),
      ("2026-10-08T08:50:00+09:00","NK225MCV2026"),
      ("2026-10-08T17:05:00+09:00","NK225MCX2026"),
      ("2026-11-12T08:50:00+09:00","NK225MCX2026"),
      ("2026-11-12T17:05:00+09:00","NK225MCZ2026"),
    ]
    results=[]
    for ts,expected in cases:
        r=m.resolve(at(ts),cal)
        ok=r["symbol"]==expected and r["continuous_contract"] is False
        results.append({"at_jst":ts,"expected":expected,"observed":r["symbol"],"pass":ok})
    exhaustion=False
    try:
        m.resolve(at("2026-12-10T17:05:00+09:00"),cal)
    except RuntimeError as exc:
        exhaustion="roll calendar exhausted" in str(exc)
    status="PASS" if all(x["pass"] for x in results) and exhaustion else "FAIL"
    print(json.dumps({"status":status,"cases":results,"calendar_exhaustion_fail_closed":exhaustion},
                     ensure_ascii=False,indent=2))
    raise SystemExit(0 if status=="PASS" else 1)

if __name__=="__main__":
    main()
