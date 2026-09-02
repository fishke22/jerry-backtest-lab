from __future__ import annotations

import hashlib
import io
import json
import os
import re
import time
import urllib.request
import zipfile
from pathlib import Path

from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"config"/"jnu_pcr_required_report_manifest_v1.json"
FREEZE=ROOT/"config"/"jnu_pcr_information_definition_freeze_v1.json"
OUT=ROOT/"pcr_results"/"jnu_pcr_information_panel_v1.json"
REPORT=ROOT/"pcr_reports"/"jnu_pcr_information_panel_v1.md"

CODE_RE=re.compile(r"(1[34]\d{7})")
MONTH_EXACT=re.compile(r"(?<!\d)(20\d{4})(?!\d)")
MODERN_PREFIX=re.compile(r"^(20\d{4})\s+\d{2}\.\d{2}\s+")
WEEKLY_PREFIX=re.compile(r"^20\d{6}\s+\d{2}\.\d{2}\s+")
TRANSITION_ISSUE=re.compile(r"(?<!\d)(20\d{4})\s+\d{2}\.\d{2}\s+([\d,]+)\s+(1[34]\d{7})\s+")
OLD_AUC=re.compile(r"(\d[\d,]*)(20\d{4})(?!\d)")
OLD_AUC_SPACED=re.compile(r"…\s*([\d ]+?)\s{2,}([\d ]+?)(20\d{4})(?!\d)")
NUM_RE=re.compile(r"(?<![A-Za-z0-9])\d[\d,]*(?:\.\d+)?")

def num(s:str)->float:
    return float(s.replace(",","").replace(" ",""))

def request_bytes(url:str, attempts:int=3)->bytes:
    last=None
    for i in range(attempts):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 JNU-research-nonprofit"})
            return urllib.request.urlopen(req,timeout=120).read()
        except Exception as e:
            last=e
            time.sleep(2*(i+1))
    raise RuntimeError(f"download failed {url}: {last!r}")

def spot_close_from_reader(reader:PdfReader)->float:
    for page in reader.pages:
        txt=page.extract_text() or ""
        lines=txt.splitlines()
        for i,line in enumerate(lines):
            normalized_line=re.sub(r"\s+","",line)
            if "参考日経平均株価" not in normalized_line:
                continue
            vals=[num(x) for x in re.findall(r"\d{1,3}(?:,\d{3})*\.\d+","\n".join(lines[i:]))]
            if len(vals)>=5:
                return vals[-2]
            # OSE report text extraction order from roughly 2016-07 through 2019-11
            # places the reference label after the OHLC/net-change row. Walk backward
            # on the same page and select the nearest line carrying the five decimals.
            for prior in reversed(lines[max(0,i-30):i]):
                vals=[num(x) for x in re.findall(r"\d{1,3}(?:,\d{3})*\.\d+",prior)]
                if len(vals)>=5:
                    return vals[-2]
    raise RuntimeError("reference Nikkei close not parsed")

def page_market(txt:str)->str|None:
    anchor=txt.find("Nikkei 225 Options")
    if anchor<0:
        return None
    body=txt[anchor:]
    pa=body.find("Auction Market"); pj=body.find("J-NET Market")
    if pa>=0 and (pj<0 or pa<pj):
        return "AUCTION"
    if pj>=0:
        return "JNET"
    pa=body.find("競争売買市場"); pj=body.find("Ｊ－ＮＥＴ市場")
    if pa>=0 and (pj<0 or pa<pj):
        return "AUCTION"
    if pj>=0:
        return "JNET"
    return None

def parse_line(line:str, market:str|None)->dict|None:
    # Weekly Nikkei 225 option rows use an 8-digit expiry date (YYYYMMDD).
    # G1 is frozen to standard monthly options, so exclude them before legacy fallbacks.
    if WEEKLY_PREFIX.match(line.lstrip()):
        return None
    cm=CODE_RE.search(line)
    if not cm:
        return None
    code=cm.group(1)
    typ="PUT" if code.startswith("13") else "CALL"

    m=MODERN_PREFIX.match(line.lstrip())
    if m:
        month=m.group(1)
        sm=re.match(r"([\d,]+)",line[cm.end():])
        if not sm:
            return None
        strike=num(sm.group(1))
        toks=NUM_RE.findall(line[:cm.start()])
        if market=="AUCTION":
            if len(toks)<8:
                volume=0.0
                mode="MODERN_AUCTION_NO_TRADE_ZERO"
            else:
                volume=num(toks[-4])
                mode="MODERN_AUCTION_EXPLICIT_TRADE_FIELDS"
        elif market=="JNET":
            if len(toks)<2:
                return None
            volume=num(toks[-2])
            mode="MODERN_JNET_EXPLICIT_TRADE_FIELDS"
        else:
            return None
        return {"month":month,"type":typ,"market":market,"strike":strike,"volume":volume,"extraction_mode":mode}

    es=OLD_AUC_SPACED.search(line)
    if es:
        volume=num(es.group(1))
        month=es.group(3)
        toks_after=NUM_RE.findall(line[es.end():])
        if len(toks_after)<2:
            return None
        strike=num(toks_after[-2])
        return {"month":month,"type":typ,"market":"AUCTION","strike":strike,"volume":volume,"extraction_mode":"LEGACY_AUCTION_SPACED_GLYPH"}

    ea=OLD_AUC.search(line)
    if ea:
        month=ea.group(2)
        toks_after=NUM_RE.findall(line[ea.end():])
        if len(toks_after)<2:
            return None
        # In legacy rows, the segment after option code and last-trading-day date
        # contains the explicit traded fields. A no-trade row contains only ellipses.
        segment=line[cm.end():ea.start(1)]
        segment=re.sub(r"^\d{2}\.\d{2}", "", segment)
        trade_tokens=NUM_RE.findall(segment)
        if trade_tokens:
            volume=num(trade_tokens[-1])
            mode="LEGACY_AUCTION_COMPACT"
        else:
            volume=0.0
            mode="LEGACY_AUCTION_NO_TRADE_ZERO"
        return {"month":month,"type":typ,"market":"AUCTION","strike":num(toks_after[-2]),"volume":volume,"extraction_mode":mode}

    mm=MONTH_EXACT.search(line)
    if mm:
        toks_before=NUM_RE.findall(line[:mm.start()])
        toks_after=NUM_RE.findall(line[mm.end():])
        if not toks_before or not toks_after:
            return None
        return {"month":mm.group(1),"type":typ,"market":"JNET","strike":num(toks_after[-1]),"volume":num(toks_before[-1]),"extraction_mode":"LEGACY_JNET"}
    return None

def parse_transition_rows(line:str,market:str|None)->list[dict]:
    matches=list(TRANSITION_ISSUE.finditer(line))
    out=[]
    for i,m in enumerate(matches):
        month,strike_s,code=m.groups()
        typ="PUT" if code.startswith("13") else "CALL"
        tail=line[m.end():matches[i+1].start() if i+1<len(matches) else len(line)]
        if market=="AUCTION":
            # Transition layout puts strike before code. Volume is the integer
            # between net-change and trading-value, not a tail-relative token:
            # ... NetChange Volume TradingValue Settlement ...
            fm=list(re.finditer(
                r"[+-]?\s*\d[\d,]*\.\d+\s+([\d,]+)\s+[\d,]+\s+\d[\d,]*\.\d+",
                tail,
            ))
            if not fm:
                volume=0.0
                mode="TRANSITION_AUCTION_NO_TRADE_ZERO"
            else:
                volume=num(fm[-1].group(1))
                mode="TRANSITION_AUCTION_EXPLICIT_TRADE_FIELDS"
        elif market=="JNET":
            # J-NET rows are OHLC + Volume + TradingValue and may contain two
            # issues on one extracted text line; each issue is segmented above.
            jm=re.search(
                r"(?:\d[\d,]*\.\d+\s+){4}([\d,]+)\s+[\d,]+",
                tail,
            )
            if not jm:
                continue
            volume=num(jm.group(1))
            mode="TRANSITION_JNET_EXPLICIT_TRADE_FIELDS"
        else:
            continue
        out.append({"month":month,"type":typ,"market":market,"strike":num(strike_s),
                    "volume":volume,"extraction_mode":mode})
    return out

def parse_options_reader(reader:PdfReader)->list[dict]:
    market=None
    rows=[]
    for page in reader.pages:
        txt=page.extract_text() or ""
        if "Nikkei 225 Options" not in txt:
            continue
        pm=page_market(txt)
        if pm:
            market=pm
        if market is None:
            continue
        for line in txt.splitlines():
            line=line.strip()
            transition=parse_transition_rows(line,market)
            if transition:
                rows.extend(transition)
                continue
            row=parse_line(line,market)
            if row:
                rows.append(row)
    return rows

def fetch_readers(date:str, ref:dict):
    if ref["source"]=="NDL":
        url=f"https://dl.ndl.go.jp/view/prepareDownload?contentNo=1&itemId=info:ndljp/pid/{ref['pid']}"
        raw=request_bytes(url)
        sha=hashlib.sha256(raw).hexdigest()
        reader=PdfReader(io.BytesIO(raw))
        return reader,reader,{"source":"NDL","identifier":ref["identifier"],"sha256":sha,"bytes":len(raw)}
    if ref["source"]=="JPX_CURRENT":
        raw=request_bytes(ref["zip_url"])
        zsha=hashlib.sha256(raw).hexdigest()
        ds=date.replace("-","")
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            opt=z.read(f"siop_dyr_{ds}.pdf")
            spot=z.read(f"sif_dyr_{ds}.pdf")
        return PdfReader(io.BytesIO(opt)),PdfReader(io.BytesIO(spot)),{
            "source":"JPX_CURRENT",
            "zip_path":ref["ose_zip_path"],
            "zip_sha256":zsha,
            "options_sha256":hashlib.sha256(opt).hexdigest(),
            "spot_sha256":hashlib.sha256(spot).hexdigest(),
        }
    raise RuntimeError(f"unknown source {ref}")

def parse_day(date:str, ref:dict)->dict:
    opt_reader,spot_reader,prov=fetch_readers(date,ref)
    spot=spot_close_from_reader(spot_reader)
    rows=parse_options_reader(opt_reader)
    months=sorted({x["month"] for x in rows})[:2]
    if len(months)<2:
        raise RuntimeError(f"{date}: less than two maturities {months}")
    legs=[]
    for m in months:
        for typ in ("PUT","CALL"):
            subset=[x for x in rows if x["month"]==m and x["type"]==typ]
            strikes=sorted({x["strike"] for x in subset})
            eligible=[x for x in strikes if x<spot] if typ=="PUT" else [x for x in strikes if x>spot]
            if not eligible:
                raise RuntimeError(f"{date}: no OTM strike {m} {typ} spot={spot}")
            strike=max(eligible) if typ=="PUT" else min(eligible)
            selected=[x for x in subset if x["strike"]==strike]
            auction=sum(x["volume"] for x in selected if x["market"]=="AUCTION")
            jnet=sum(x["volume"] for x in selected if x["market"]=="JNET")
            legs.append({
                "month":m,"type":typ,"strike":strike,
                "auction_volume":auction,"jnet_volume":jnet,
                "ose_total_volume":auction+jnet,
                "extraction_modes":sorted({x["extraction_mode"] for x in selected}),
            })
    put=sum(x["ose_total_volume"] for x in legs if x["type"]=="PUT")
    call=sum(x["ose_total_volume"] for x in legs if x["type"]=="CALL")
    if call==0:
        daily=None
        reason="ZERO_SELECTED_CALL_DENOMINATOR"
    else:
        daily=100*put/call
        reason=None
    return {
        "date":date,"spot_close":spot,"maturities":months,"legs":legs,
        "selected_put_volume":put,"selected_call_volume":call,
        "daily_pcr":daily,"undefined_reason":reason,
        "parsed_issue_rows":len(rows),"provenance":prov,
    }

def main():
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    freeze=json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["formal_directional_family_opened"] is False
    wanted=os.environ.get("PCR_SMOKE_MONTHS","").strip()
    smoke=set(x.strip() for x in wanted.split(",") if x.strip()) if wanted else None
    yr=os.environ.get("PCR_YEAR_RANGE","").strip()
    year_range=None
    if yr:
        a,b=yr.split("-",1)
        year_range=(int(a),int(b))
    months=[]
    for m in manifest["months"]:
        if smoke is not None and m["month"] not in smoke:
            continue
        if year_range is not None:
            y=int(m["month"][:4])
            if y<year_range[0] or y>year_range[1]:
                continue
        rec={"month":m["month"],"archive_complete":m["archive_complete"],"days":[]}
        if not m["archive_complete"]:
            rec["status"]="ARCHIVE_INCOMPLETE"
            rec["missing_dates"]=[x["date"] for x in m["required_dates"] if x["source_ref"] is None]
            months.append(rec)
            print(m["month"],rec["status"],flush=True)
            continue
        failed=None
        for d in m["required_dates"]:
            try:
                day=parse_day(d["date"],d["source_ref"])
                rec["days"].append(day)
                print(m["month"],d["date"],"OK",day["daily_pcr"],day["undefined_reason"],flush=True)
            except Exception as e:
                failed=repr(e)
                rec["days"].append({"date":d["date"],"error":failed})
                print(m["month"],d["date"],"ERROR",failed,flush=True)
                break
            time.sleep(0.15)
        if failed:
            rec["status"]="PARSER_OR_SOURCE_ERROR"
            rec["error"]=failed
        else:
            defined=[x for x in rec["days"] if x.get("daily_pcr") is not None]
            if len(defined)==5:
                rec["status"]="PCR_DEFINED"
                rec["monthly_pcr"]=sum(x["daily_pcr"] for x in defined)/5
            else:
                rec["status"]="PCR_UNDEFINED_REQUIRED_DAY"
                rec["monthly_pcr"]=None
                rec["undefined_dates"]=[x["date"] for x in rec["days"] if x.get("daily_pcr") is None]
        months.append(rec)

    statuses={}
    for m in months:
        statuses[m["status"]]=statuses.get(m["status"],0)+1
    result={
        "version":"1.0","as_of":"2026-09-01",
        "candidate_id":manifest["candidate_id"],
        "directional_return_outcomes_used":False,
        "formal_directional_family_opened":False,
        "smoke_months":sorted(smoke) if smoke is not None else None,
        "year_range":list(year_range) if year_range is not None else None,
        "status_counts":statuses,"months":months,
    }
    OUT.parent.mkdir(exist_ok=True)
    REPORT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(
        "# JNU PCR information panel v1\n\n"
        + "- Directional return outcomes used: **false**\n"
        + "- Formal directional family opened: **false**\n"
        + "- Status counts: "+json.dumps(statuses,ensure_ascii=False)+"\n"
        + "- Smoke months: "+json.dumps(result["smoke_months"],ensure_ascii=False)+"\n",
        encoding="utf-8",
    )
    print("FINAL",json.dumps(statuses),flush=True)
    if "PARSER_OR_SOURCE_ERROR" in statuses:
        raise SystemExit(2)

if __name__=="__main__":
    main()
