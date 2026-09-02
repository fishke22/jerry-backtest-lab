from __future__ import annotations
import hashlib, io, json, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"flow_results"/"jnu_jpx_cash_foreign_flow_pit_panel_v1.json"
BASE="https://www.jpx.co.jp"
PAGES=[BASE+"/english/markets/statistics-equities/investor-type/"]+[BASE+f"/english/markets/statistics-equities/investor-type/00-00-archives-{i:02d}.html" for i in range(0,11)]
HOLIDAY_URL="https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv"
HOLIDAY_SHA="cec37a743c96995cdb9cb52b685c9003634682a9b0e1a640a6b9b96881fe964a"

def sha(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def get(url:str,tries:int=3)->bytes:
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 JNU research"})
    last=None
    for i in range(tries):
        try:
            with urllib.request.urlopen(req,timeout=30) as r:
                return r.read()
        except Exception as e:
            last=e; time.sleep(1.2*(i+1))
    raise RuntimeError(f"download failed {url}: {last}")

def holidays()->set[date]:
    b=get(HOLIDAY_URL)
    if sha(b)!=HOLIDAY_SHA:
        raise RuntimeError("Cabinet Office holiday CSV hash changed")
    out=set()
    for line in b.splitlines():
        first=line.split(b",",1)[0].strip()
        try:
            y,m,d=(int(x) for x in first.decode("ascii").split("/"))
            out.add(date(y,m,d))
        except Exception:
            pass
    return out

def biz(x:date,h:set[date])->bool:
    return x.weekday()<5 and x not in h and (x.month,x.day) not in {(1,2),(1,3),(12,31)}

def pit_date(covered_to:date,h:set[date]):
    mon=covered_to+timedelta(days=7-covered_to.weekday())
    week=[mon+timedelta(days=i) for i in range(7)]
    b=[x for x in week if biz(x,h)]
    if len(b)<4: return None,b
    return b[3],b

def next_biz(x:date,h:set[date])->date:
    y=x+timedelta(days=1)
    while not biz(y,h): y+=timedelta(days=1)
    return y

def discover()->list[str]:
    rx=re.compile(r'href="([^"]+stock_val_1_[^"]+\.xls)"')
    urls=set()
    for p in PAGES:
        try:
            text=get(p).decode("utf-8","ignore")
        except Exception:
            continue
        for m in rx.finditer(text):
            u=m.group(1)
            if u.startswith("/"): u=BASE+u
            urls.add(u)
    return sorted(urls)

def parse_period(df:pd.DataFrame)->tuple[date,date,str]:
    txt=" ".join(str(x) for x in df.iloc[3].tolist() if pd.notna(x))
    m=re.search(r'(20\d{2})/(\d{1,2})\s*week\d+\s*\(\s*(\d{1,2})/(\d{1,2})\s*-\s*(\d{1,2})/(\d{1,2})\s*\)',txt)
    if not m:
        raise ValueError(f"period parse failed: {txt}")
    y=int(m.group(1)); sm=int(m.group(3)); sd=int(m.group(4)); em=int(m.group(5)); ed=int(m.group(6))
    sy=y
    ey=y+1 if sm==12 and em==1 else y
    return date(sy,sm,sd),date(ey,em,ed),txt

def parse_one(url:str,h:set[date])->dict:
    b=get(url)
    source_hash=sha(b)
    df=pd.read_excel(io.BytesIO(b),sheet_name="Tokyo & Nagoya",header=None,engine="xlrd")
    cfrom,cto,label=parse_period(df)
    sales_rows=[]
    purch_rows=[]
    for _,row in df.iterrows():
        c0=str(row.iloc[0]) if len(row)>0 and pd.notna(row.iloc[0]) else ""
        c2=str(row.iloc[2]) if len(row)>2 and pd.notna(row.iloc[2]) else ""
        if "海外投資家" in c0 and c2=="Sales":
            sales_rows.append(row)
        if "Foreigners" in c0 and c2=="Purchases":
            purch_rows.append(row)
    if len(sales_rows)!=1 or len(purch_rows)!=1:
        raise ValueError(f"Foreigners row count sales={len(sales_rows)} purchases={len(purch_rows)}")
    sales=float(str(sales_rows[0].iloc[8]).replace(",",""))
    purch=float(str(purch_rows[0].iloc[8]).replace(",",""))
    net=purch-sales
    pub,business=pit_date(cto,h)
    if pub is None:
        pit_status="PIT_TIMING_IRREGULAR_EXCLUDED"; use=None
    else:
        pit_status="PIT_STANDARD_RULE_ELIGIBLE"; use=next_biz(pub,h)
    return {
        "covered_from":cfrom.isoformat(),
        "covered_to":cto.isoformat(),
        "period_label":label,
        "foreign_flow_sign":1 if net>0 else (-1 if net<0 else 0),
        "foreign_net_value_retained":False,
        "pit_status":pit_status,
        "publication_date":pub.isoformat() if pub else None,
        "publication_time_jst":"15:30" if pub else None,
        "earliest_signal_use_date":use.isoformat() if use else None,
        "next_week_regular_business_days":[x.isoformat() for x in business],
        "source_url":url,
        "source_sha256":source_hash,
        "directional_return_used":False,
    }

def main():
    h=holidays()
    urls=discover()
    records=[]; errors=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs={ex.submit(parse_one,u,h):u for u in urls}
        for fut in as_completed(futs):
            u=futs[fut]
            try: records.append(fut.result())
            except Exception as e: errors.append({"source_url":u,"error":str(e)})
    records.sort(key=lambda r:(r["covered_from"],r["covered_to"]))
    # Keep the preregistered sample start only.
    records=[r for r in records if r["covered_from"]>="2016-01-01"]
    urls_2016plus=[u for u in urls if re.search(r'stock_val_1_(?:1[6-9]|2[0-6])',u)]
    dup=[]
    seen=set()
    for r in records:
        k=(r["covered_from"],r["covered_to"])
        if k in seen: dup.append(k)
        seen.add(k)
    eligible=[r for r in records if r["pit_status"]=="PIT_STANDARD_RULE_ELIGIBLE"]
    irregular=[r for r in records if r["pit_status"]!="PIT_STANDARD_RULE_ELIGIBLE"]
    total=len(records)
    parse_fraction=total/(total+len(errors)) if total+len(errors) else 0.0
    gate={
        "discovered_candidate_urls":len(urls),
        "parsed_sample_weeks":total,
        "parse_errors":len(errors),
        "parse_success_fraction":parse_fraction,
        "minimum_500_weeks_pass":total>=500,
        "minimum_95pct_parse_pass":parse_fraction>=0.95,
        "zero_parser_errors_pass":len(errors)==0,
        "duplicate_periods":len(dup),
        "duplicate_periods_pass":len(dup)==0,
        "pit_standard_eligible_weeks":len(eligible),
        "pit_irregular_excluded_weeks":len(irregular),
        "pit_irregular_fraction":len(irregular)/total if total else 1.0,
        "pit_irregular_fraction_pass":(len(irregular)/total if total else 1.0)<=0.05,
        "directional_returns_used":False,
    }
    out={
        "version":"1.0",
        "candidate_id":"JPX_CASH_FOREIGN_FLOW_TOKYO_NAGOYA_SIGN_G1",
        "status":"SOURCE_PIT_PANEL_BUILT_NO_RETURNS",
        "gate":gate,
        "errors":errors,
        "records":records,
        "directional_outcome_inspected":False,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":out["status"],"gate":gate,"first":records[0] if records else None,"last":records[-1] if records else None,"output":str(OUT)},indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
