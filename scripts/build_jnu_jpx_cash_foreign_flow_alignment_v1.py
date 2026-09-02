from __future__ import annotations
import csv,hashlib,json
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIT=ROOT/"flow_results"/"jnu_jpx_cash_foreign_flow_pit_panel_v1.json"
FRED=Path(r"D:\Temp\nikkei225_2016_20260902.csv")
OUT=ROOT/"flow_results"/"jnu_jpx_cash_foreign_flow_alignment_v1.json"

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def main():
    pit=json.loads(PIT.read_text(encoding="utf-8"))
    if pit.get("directional_outcome_inspected") is not False: raise RuntimeError("outcome guard")
    dates=[]
    with FRED.open(encoding="utf-8",newline="") as f:
        rd=csv.reader(f); next(rd)
        for row in rd:
            if len(row)<2 or row[1].strip() in {"",".","NA","NaN"}: continue
            dates.append(date.fromisoformat(row[0]))
    dates=sorted(set(dates)); idx={d:i for i,d in enumerate(dates)}
    records=[]; incomplete=[]
    for r in pit["records"]:
        if r["pit_status"]!="PIT_STANDARD_RULE_ELIGIBLE": continue
        earliest=date.fromisoformat(r["earliest_signal_use_date"])
        entry=next((d for d in dates if d>=earliest),None)
        if entry is None:
            incomplete.append({"covered_from":r["covered_from"],"reason":"NO_ENTRY_DATE"}); continue
        i=idx[entry]
        if i+5>=len(dates):
            incomplete.append({"covered_from":r["covered_from"],"publication_date":r["publication_date"],"entry_date":entry.isoformat(),"reason":"FIFTH_EXIT_NOT_AVAILABLE"}); continue
        records.append({
            "covered_from":r["covered_from"],
            "covered_to":r["covered_to"],
            "publication_date":r["publication_date"],
            "publication_time_jst":"15:30",
            "entry_date":entry.isoformat(),
            "exit_date":dates[i+5].isoformat(),
            "holding_intervals":5,
            "foreign_flow_sign":int(r["foreign_flow_sign"]),
            "source_sha256":r["source_sha256"],
        })
    n=len(records)
    if n<300: raise RuntimeError(f"minimum observations failed {n}")
    base=n//4; rem=n%4; sizes=[base+(1 if i<rem else 0) for i in range(4)]
    blocks=[]; pos=0
    for bi,sz in enumerate(sizes,1):
        chunk=records[pos:pos+sz]
        for row in chunk: row["subperiod"]=bi
        blocks.append({"subperiod":bi,"n":sz,"from":chunk[0]["publication_date"],"to":chunk[-1]["publication_date"]})
        pos+=sz
    out={
        "version":"1.0","candidate_id":"JPX_CASH_FOREIGN_FLOW_TOKYO_NAGOYA_SIGN_G1",
        "status":"ALIGNMENT_FROZEN_BEFORE_PRICE_VALUE_READ",
        "pit_panel_sha256":sha(PIT),"fred_calendar_csv_sha256":sha(FRED),
        "price_values_parsed":False,"price_values_used_for_boundaries":False,
        "eligible_complete_observations":n,"incomplete_recent_observations":len(incomplete),
        "subperiods":blocks,"incomplete":incomplete,"records":records,
        "directional_outcome_inspected":False
    }
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in out.items() if k not in {"records","incomplete"}}|{"incomplete":incomplete},indent=2,ensure_ascii=False))
if __name__=="__main__": main()
