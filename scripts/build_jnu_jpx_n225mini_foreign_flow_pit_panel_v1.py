from __future__ import annotations
import csv, hashlib, io, json, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"flow_results"/"jnu_jpx_n225mini_foreign_flow_information_panel_v1.json"
OUT=ROOT/"flow_results"/"jnu_jpx_n225mini_foreign_flow_pit_panel_v1.json"
HOLIDAY_URL="https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv"
EXPECTED_HOLIDAY_SHA="cec37a743c96995cdb9cb52b685c9003634682a9b0e1a640a6b9b96881fe964a"
JST=ZoneInfo("Asia/Tokyo")

def sha_bytes(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def get(url:str,method:str="GET")->tuple[bytes,dict]:
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 JNU research"},method=method)
    with urllib.request.urlopen(req,timeout=30) as r:
        return (r.read() if method=="GET" else b""), dict(r.headers.items())

def load_holidays()->set[date]:
    b,_=get(HOLIDAY_URL)
    got=sha_bytes(b)
    if got!=EXPECTED_HOLIDAY_SHA:
        raise RuntimeError(f"Cabinet Office holiday CSV hash changed: {got}")
    out=set()
    for line in b.splitlines():
        first=line.split(b",",1)[0].strip()
        try:
            s=first.decode("ascii")
            y,m,d=(int(x) for x in s.split("/"))
            out.add(date(y,m,d))
        except Exception:
            continue
    return out

def regular_business_day(x:date,holidays:set[date])->bool:
    if x.weekday()>=5:
        return False
    if x in holidays:
        return False
    if (x.month,x.day) in {(1,2),(1,3),(12,31)}:
        return False
    return True

def next_week_monday(covered_to:date)->date:
    return covered_to + timedelta(days=(7-covered_to.weekday()))

def fourth_business_day_next_week(covered_to:date,holidays:set[date]):
    mon=next_week_monday(covered_to)
    days=[mon+timedelta(days=i) for i in range(7)]
    biz=[x for x in days if regular_business_day(x,holidays)]
    if len(biz)<4:
        return None,biz
    return biz[3],biz

def next_regular_business_day(x:date,holidays:set[date])->date:
    y=x+timedelta(days=1)
    while not regular_business_day(y,holidays):
        y+=timedelta(days=1)
    return y

def head_last_modified(rec:dict)->dict:
    try:
        _,h=get(rec["source_url"],method="HEAD")
        lm=h.get("Last-Modified") or h.get("last-modified")
        if not lm:
            return {"source_url":rec["source_url"],"status":"NO_LAST_MODIFIED"}
        dt=parsedate_to_datetime(lm)
        if dt.tzinfo is None:
            dt=dt.replace(tzinfo=timezone.utc)
        jst=dt.astimezone(JST)
        inferred=date.fromisoformat(rec["publication_date"])
        return {
            "source_url":rec["source_url"],
            "status":"OK",
            "last_modified_utc":dt.isoformat(),
            "last_modified_jst":jst.isoformat(),
            "last_modified_jst_date":jst.date().isoformat(),
            "inferred_publication_date":inferred.isoformat(),
            "date_match":jst.date()==inferred,
            "time_1530_match":(jst.hour,jst.minute)==(15,30),
        }
    except Exception as e:
        return {"source_url":rec["source_url"],"status":"HEAD_ERROR","error":str(e)}

def main():
    src=json.loads(SRC.read_text(encoding="utf-8"))
    if src.get("directional_outcome_inspected") is not False:
        raise RuntimeError("fail closed: source panel already marked outcome-inspected")
    holidays=load_holidays()
    records=[]; irregular=[]
    for r in src["records"]:
        cto=datetime.strptime(r["covered_to"],"%Y%m%d").date()
        pub,biz=fourth_business_day_next_week(cto,holidays)
        x=dict(r)
        x.pop("foreign_sales_value",None)
        x.pop("foreign_purchases_value",None)
        # Keep only sign sufficient statistic in durable PIT panel.
        net=int(r["foreign_net_value"])
        x["foreign_flow_sign"]=1 if net>0 else (-1 if net<0 else 0)
        x["foreign_net_value_retained"]=False
        if pub is None:
            x.update({
                "pit_status":"PIT_TIMING_IRREGULAR_EXCLUDED",
                "publication_date":None,
                "publication_time_jst":None,
                "earliest_signal_use_date":None,
                "next_week_regular_business_days":[z.isoformat() for z in biz],
            })
            irregular.append({"covered_from":r["covered_from"],"covered_to":r["covered_to"],"business_days":[z.isoformat() for z in biz]})
        else:
            use=next_regular_business_day(pub,holidays)
            x.update({
                "pit_status":"PIT_STANDARD_RULE_ELIGIBLE",
                "publication_date":pub.isoformat(),
                "publication_time_jst":"15:30",
                "earliest_signal_use_date":use.isoformat(),
                "next_week_regular_business_days":[z.isoformat() for z in biz],
            })
        records.append(x)

    eligible=[r for r in records if r["pit_status"]=="PIT_STANDARD_RULE_ELIGIBLE"]
    irr_frac=len(irregular)/len(records) if records else 1.0

    # Recent-file audit: only 2026 records and only if server timestamp itself is in 2026.
    recent=[r for r in eligible if r["covered_to"].startswith("2026")]
    audits=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs={ex.submit(head_last_modified,r):r for r in recent}
        for fut in as_completed(futs):
            audits.append(fut.result())
    current_2026=[]
    for a in audits:
        if a.get("status")=="OK" and a.get("last_modified_jst","").startswith("2026-"):
            current_2026.append(a)
    date_matches=sum(1 for a in current_2026 if a.get("date_match"))
    time_matches=sum(1 for a in current_2026 if a.get("time_1530_match"))

    gate={
        "total_source_weeks":len(records),
        "pit_standard_eligible_weeks":len(eligible),
        "pit_irregular_excluded_weeks":len(irregular),
        "pit_irregular_exclusion_fraction":irr_frac,
        "maximum_irregular_exclusion_fraction":0.05,
        "irregular_fraction_pass":irr_frac<=0.05,
        "directional_returns_used":False,
        "recent_2026_http_timestamp_auditable_files":len(current_2026),
        "recent_2026_publication_date_matches":date_matches,
        "recent_2026_publication_time_1530_matches":time_matches,
        "recent_2026_date_match_fraction":date_matches/len(current_2026) if current_2026 else None,
        "recent_2026_time_match_fraction":time_matches/len(current_2026) if current_2026 else None,
    }
    out={
        "version":"1.0",
        "candidate_id":"JPX_N225MINI_FOREIGN_FLOW_SIGN_G1",
        "status":"PIT_TIMING_PANEL_BUILT_NO_RETURNS",
        "holiday_source_url":HOLIDAY_URL,
        "holiday_source_sha256":EXPECTED_HOLIDAY_SHA,
        "gate":gate,
        "irregular_weeks":irregular,
        "recent_http_audit":sorted(audits,key=lambda x:x.get("source_url","")),
        "records":records,
        "directional_outcome_inspected":False,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":out["status"],"gate":gate,"irregular_sample":irregular[:10],"output":str(OUT)},indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
