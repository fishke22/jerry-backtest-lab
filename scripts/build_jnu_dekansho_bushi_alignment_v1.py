from __future__ import annotations
import csv, hashlib, json
from datetime import date
from pathlib import Path

ROOT=Path(r"D:\JERRY_BACKTEST_CLOUD_SYNC_20260831")
CSV=Path(r"D:\Temp\nikkei225_2014_20260831.csv")
OUT=ROOT/"config"/"jnu_dekansho_bushi_postpublication_alignment_v1.json"

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def month_key(d:date)->str:
    return f"{d.year:04d}-{d.month:02d}"

def main():
    valid=[]
    with CSV.open(encoding="utf-8",newline="") as f:
        rd=csv.reader(f)
        header=next(rd)
        if header[:2] != ["observation_date","NIKKEI225"]:
            raise RuntimeError(f"unexpected header: {header}")
        for row in rd:
            if len(row)<2: continue
            # Date/alignment phase only: inspect presence, never parse price value.
            if row[1].strip() in {"",".","NA","NaN"}: continue
            valid.append(date.fromisoformat(row[0]))
    valid=sorted(set(valid))
    pre=[d for d in valid if d < date(2014,1,1)]
    sample=[d for d in valid if date(2014,1,1)<=d<=date(2026,8,31)]
    if not pre:
        raise RuntimeError("no prior valid close available for first 2014 return")
    all_dates=pre+sample
    idx={d:i for i,d in enumerate(all_dates)}

    expected=[]
    y,m=2014,1
    while (y,m)<=(2026,8):
        expected.append(f"{y:04d}-{m:02d}")
        m+=1
        if m==13:
            y+=1; m=1
    present=sorted({month_key(d) for d in sample})
    missing=sorted(set(expected)-set(present))
    if missing:
        raise RuntimeError(f"missing calendar months: {missing}")
    if len(expected)!=152:
        raise RuntimeError(f"expected 152 months, got {len(expected)}")

    # Four equal chronological blocks, frozen before numeric price parsing.
    blocks=[]
    monthly=[]
    month_to_sub={}
    for i in range(4):
        chunk=expected[i*38:(i+1)*38]
        blocks.append({
            "subperiod":i+1,
            "n_months":len(chunk),
            "first_month":chunk[0],
            "last_month":chunk[-1]
        })
        for mk in chunk: month_to_sub[mk]=i+1

    daily=[]
    prev_position=0
    for d in sample:
        i=idx[d]
        if i==0: raise RuntimeError("first sample date lacks prior date")
        prev=all_dates[i-1]
        pos=1 if d.month<=6 else -1
        units=abs(pos-prev_position)
        daily.append({
            "return_date":d.isoformat(),
            "prior_valid_close_date":prev.isoformat(),
            "month":month_key(d),
            "position":pos,
            "transition_cost_units":units,
            "subperiod":month_to_sub[month_key(d)]
        })
        prev_position=pos

    for mk in expected:
        rr=[x for x in daily if x["month"]==mk]
        monthly.append({
            "month":mk,
            "position":rr[0]["position"],
            "subperiod":month_to_sub[mk],
            "trading_return_days":len(rr),
            "first_return_date":rr[0]["return_date"],
            "last_return_date":rr[-1]["return_date"],
            "transition_cost_units_in_month":sum(x["transition_cost_units"] for x in rr)
        })

    transition_days=[x for x in daily if x["transition_cost_units"]>0]
    out={
        "version":"1.0",
        "candidate_id":"NIKKEI_DEKANSHO_BUSHI_POSTPUBLICATION_G1",
        "status":"ALIGNMENT_FROZEN_BEFORE_PRICE_VALUE_READ",
        "fred_csv_sha256":sha(CSV),
        "fred_source":"FRED NIKKEI225 bounded 2013-12-20 through 2026-08-31",
        "price_values_parsed":False,
        "directional_outcome_inspected":False,
        "sample_months":len(expected),
        "sample_first_month":expected[0],
        "sample_last_month":expected[-1],
        "daily_return_observations":len(daily),
        "four_subperiods":blocks,
        "recent_window_months":36,
        "transition_days":transition_days,
        "monthly_alignment":monthly,
        "daily_alignment":daily
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":out["status"],
        "sample_months":out["sample_months"],
        "daily_return_observations":out["daily_return_observations"],
        "subperiods":blocks,
        "transition_days":transition_days,
        "fred_csv_sha256":out["fred_csv_sha256"]
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
