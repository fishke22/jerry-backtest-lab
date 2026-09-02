from __future__ import annotations
import csv, hashlib, io, json, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE="https://www.jpx.co.jp"
ARCHIVE="https://www.jpx.co.jp/english/markets/statistics-derivatives/sector/00-archives-{i:02d}.html"
TARGET_PRODUCT="313"
TARGET_INVESTOR="60"
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"flow_results"/"jnu_jpx_n225mini_foreign_flow_information_panel_v1.json"

def get(url:str,tries:int=3)->bytes:
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 JNU research"})
    last=None
    for i in range(tries):
        try:
            with urllib.request.urlopen(req,timeout=30) as r:
                return r.read()
        except Exception as e:
            last=e; time.sleep(1.5*(i+1))
    raise RuntimeError(f"download failed {url}: {last}")

def sha(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def discover()->list[str]:
    urls=[]
    rx=re.compile(r'href="([^"]+Tousi_DV_W_[^"]+\.csv)"')
    for i in range(11):
        b=get(ARCHIVE.format(i=i))
        text=b.decode("utf-8","ignore")
        for m in rx.finditer(text):
            u=m.group(1)
            if u.startswith("/"): u=BASE+u
            urls.append(u)
    return sorted(set(urls))

def parse_one(url:str)->dict:
    b=get(url)
    h=sha(b)
    # New bilingual header format from Apr 2026.
    text=b.decode("utf-8-sig","replace")
    first=text.splitlines()[0] if text.splitlines() else ""
    if "Product type" in first:
        rows=list(csv.reader(io.StringIO(text)))
        head=rows[0]
        found=[]
        for r in rows[1:]:
            if len(r)<12: continue
            if r[0].strip('"')==TARGET_PRODUCT and r[5].strip('"')==TARGET_INVESTOR and r[6].strip('"')=="2":
                sales=int(float(r[7])); purchases=int(float(r[9]))
                found.append((r,sales,purchases))
        if len(found)!=1:
            raise ValueError(f"new-format target row count={len(found)}")
        r,sales,purchases=found[0]
        return {
            "covered_from":r[3].strip('"'),
            "covered_to":r[4].strip('"'),
            "year_week":r[2].strip('"'),
            "foreign_sales_value":sales,
            "foreign_purchases_value":purchases,
            "foreign_net_value":purchases-sales,
            "format":"NEW_2026_BILINGUAL",
            "source_url":url,
            "source_sha256":h,
            "directional_return_used":False
        }
    # Legacy numeric CSV.
    rows=list(csv.reader(io.StringIO(text)))
    found=[]
    for r in rows:
        if len(r)<24: continue
        if r[0].strip()==TARGET_PRODUCT and r[7].strip()==TARGET_INVESTOR:
            sales=int(float(r[11])); purchases=int(float(r[17]))
            found.append((r,sales,purchases))
    if len(found)!=1:
        raise ValueError(f"legacy target row count={len(found)}")
    r,sales,purchases=found[0]
    return {
        "covered_from":r[5],
        "covered_to":r[6],
        "year_week":r[4],
        "foreign_sales_value":sales,
        "foreign_purchases_value":purchases,
        "foreign_net_value":purchases-sales,
        "format":"LEGACY_NUMERIC",
        "source_url":url,
        "source_sha256":h,
        "directional_return_used":False
    }

def main():
    urls=discover()
    results=[]; errors=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs={ex.submit(parse_one,u):u for u in urls}
        for fut in as_completed(futs):
            u=futs[fut]
            try: results.append(fut.result())
            except Exception as e: errors.append({"source_url":u,"error":str(e)})
    results.sort(key=lambda x:(x["covered_from"],x["covered_to"]))
    dup=[]
    seen=set()
    for x in results:
        k=(x["covered_from"],x["covered_to"])
        if k in seen: dup.append(k)
        seen.add(k)
    gate={
        "discovered_weekly_csv":len(urls),
        "parsed_target_weeks":len(results),
        "parse_errors":len(errors),
        "parse_success_fraction":len(results)/len(urls) if urls else 0,
        "minimum_weekly_reports_pass":len(urls)>=500,
        "minimum_parse_fraction_pass":(len(results)/len(urls) if urls else 0)>=0.95,
        "zero_parser_source_errors_pass":len(errors)==0,
        "duplicate_periods":len(dup),
        "duplicate_periods_pass":len(dup)==0
    }
    out={
        "version":"1.0",
        "candidate_id":"JPX_N225MINI_FOREIGN_FLOW_SIGN_G1",
        "status":"SOURCE_PANEL_BUILT_NO_RETURNS",
        "target":{"product_code":"313","product":"Nikkei 225 mini","investor_code":"60","investor":"Foreigners","measure":"trading value"},
        "gate":gate,
        "directional_outcome_inspected":False,
        "publication_timing_attached":False,
        "records":results,
        "errors":errors
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"status":out["status"],"gate":gate,"first":results[0] if results else None,"last":results[-1] if results else None,"output":str(OUT)},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
