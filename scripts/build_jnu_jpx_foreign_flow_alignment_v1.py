from __future__ import annotations
import csv, hashlib, json
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PIT=ROOT/"flow_results"/"jnu_jpx_n225mini_foreign_flow_pit_panel_v1.json"
FRED=Path(r"D:\Temp\nikkei225_2016_20260902.csv")
OUT=ROOT/"flow_results"/"jnu_jpx_n225mini_foreign_flow_alignment_v1.json"

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def main():
    pit=json.loads(PIT.read_text(encoding="utf-8"))
    if pit.get("directional_outcome_inspected") is not False:
        raise RuntimeError("PIT panel outcome-inspection guard failed")

    trading_dates=[]
    with FRED.open(encoding="utf-8",newline="") as f:
        rd=csv.reader(f)
        head=next(rd)
        for row in rd:
            if len(row)<2: continue
            # Only use value presence to identify an available observation; never parse the numeric price.
            if row[1].strip() in {"",".","NA","NaN"}: continue
            trading_dates.append(date.fromisoformat(row[0]))
    trading_dates=sorted(set(trading_dates))
    idx={d:i for i,d in enumerate(trading_dates)}

    eligible=[]
    incomplete=[]
    for r in pit["records"]:
        if r["pit_status"]!="PIT_STANDARD_RULE_ELIGIBLE":
            continue
        earliest=date.fromisoformat(r["earliest_signal_use_date"])
        candidates=[d for d in trading_dates if d>=earliest]
        if not candidates:
            incomplete.append({"covered_from":r["covered_from"],"reason":"NO_ENTRY_DATE"})
            continue
        entry=candidates[0]
        i=idx[entry]
        if i+5>=len(trading_dates):
            incomplete.append({"covered_from":r["covered_from"],"publication_date":r["publication_date"],"entry_date":entry.isoformat(),"reason":"FIFTH_EXIT_NOT_AVAILABLE"})
            continue
        exitd=trading_dates[i+5]
        eligible.append({
            "covered_from":r["covered_from"],
            "covered_to":r["covered_to"],
            "publication_date":r["publication_date"],
            "publication_time_jst":"15:30",
            "entry_date":entry.isoformat(),
            "exit_date":exitd.isoformat(),
            "holding_intervals":5,
            "foreign_flow_sign":int(r["foreign_flow_sign"]),
            "source_sha256":r["source_sha256"],
        })

    n=len(eligible)
    if n<300:
        raise RuntimeError(f"minimum 300 eligible observations failed: {n}")
    # Four contiguous blocks by observation count, determined before price values are parsed.
    base=n//4
    rem=n%4
    sizes=[base+(1 if i<rem else 0) for i in range(4)]
    pos=0
    blocks=[]
    for bi,sz in enumerate(sizes,1):
        chunk=eligible[pos:pos+sz]
        for row in chunk:
            row["subperiod"]=bi
        blocks.append({
            "subperiod":bi,
            "n":sz,
            "first_publication_date":chunk[0]["publication_date"],
            "last_publication_date":chunk[-1]["publication_date"],
            "first_entry_date":chunk[0]["entry_date"],
            "last_exit_date":chunk[-1]["exit_date"],
        })
        pos+=sz

    out={
        "version":"1.0",
        "candidate_id":"JPX_N225MINI_FOREIGN_FLOW_SIGN_G1",
        "status":"ALIGNMENT_FROZEN_BEFORE_PRICE_VALUE_READ",
        "pit_panel_sha256":sha(PIT),
        "fred_calendar_csv_sha256":sha(FRED),
        "fred_calendar_source":"FRED NIKKEI225 bounded 2016-01-01 through 2026-09-02",
        "price_values_parsed":False,
        "price_values_used_for_boundaries":False,
        "eligible_complete_observations":n,
        "incomplete_recent_observations":len(incomplete),
        "subperiods":blocks,
        "incomplete":incomplete,
        "records":eligible,
        "directional_outcome_inspected":False,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in out.items() if k not in {"records","incomplete"}} | {"incomplete_sample":incomplete[:10]},indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
