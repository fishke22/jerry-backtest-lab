from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
JST=timezone(timedelta(hours=9))
CAL=ROOT/"config"/"jnu_exact_micro_contract_roll_calendar_v1.json"

def parse_dt(s:str)->datetime:
    x=datetime.fromisoformat(s)
    if x.tzinfo is None:
        raise RuntimeError("roll-calendar timestamps must be offset-aware")
    return x.astimezone(JST)

def load_calendar()->dict:
    x=json.loads(CAL.read_text(encoding="utf-8"))
    entries=x.get("entries")
    if not isinstance(entries,list) or not entries:
        raise RuntimeError("roll calendar entries missing")
    prev_until=None
    for e in entries:
        start=parse_dt(e["active_from_jst"])
        end=parse_dt(e["active_until_jst"])
        if end<=start:
            raise RuntimeError(f"invalid roll interval for {e.get('symbol')}")
        if prev_until is not None and start!=prev_until:
            raise RuntimeError("roll calendar intervals must be contiguous")
        prev_until=end
        s=str(e.get("symbol",""))
        if not (s.startswith("NK225MC") and len(s)==12):
            raise RuntimeError(f"invalid individual Micro symbol in calendar: {s}")
    return x

def resolve(at:datetime, cal:dict)->dict:
    now=at.astimezone(JST)
    entries=cal["entries"]
    for i,e in enumerate(entries):
        start=parse_dt(e["active_from_jst"])
        end=parse_dt(e["active_until_jst"])
        if start<=now<end:
            return {
                "version":"1.0",
                "status":"FRONT_INDIVIDUAL_MICRO_RESOLVED",
                "resolved_at_jst":now.isoformat(),
                "symbol":e["symbol"],
                "contract_month":e["contract_month"],
                "last_trading_day":e["last_trading_day"],
                "active_from_jst":start.isoformat(),
                "active_until_jst":end.isoformat(),
                "next_symbol":entries[i+1]["symbol"] if i+1<len(entries) else None,
                "continuous_contract":False,
                "calendar":"config/jnu_exact_micro_contract_roll_calendar_v1.json",
                "discovery_snapshot":e.get("discovery_snapshot_20260906"),
            }
    first=parse_dt(entries[0]["active_from_jst"])
    last=parse_dt(entries[-1]["active_until_jst"])
    if now<first:
        raise RuntimeError(f"roll calendar not active yet: now={now.isoformat()} first={first.isoformat()}")
    raise RuntimeError(
        "roll calendar exhausted; fail closed and freeze a new calendar before probing: "
        f"now={now.isoformat()} last={last.isoformat()}"
    )

def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--at-jst",help="Synthetic/selftest resolution time; offset-aware ISO8601.")
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    if args.at_jst:
        at=datetime.fromisoformat(args.at_jst)
        if at.tzinfo is None:
            raise RuntimeError("--at-jst must be offset-aware")
    else:
        at=datetime.now(JST)
    result=resolve(at,load_calendar())
    s=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(s+"\n",encoding="utf-8")
    print(s)

if __name__=="__main__":
    main()
