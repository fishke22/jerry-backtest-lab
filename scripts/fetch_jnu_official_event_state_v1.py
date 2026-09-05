from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pdfplumber
import requests
from bs4 import BeautifulSoup

TAIPEI = ZoneInfo("Asia/Taipei")
TOKYO = ZoneInfo("Asia/Tokyo")
EASTERN = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "config" / "jnu_official_event_state_protocol_v1_1.json"

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

STATIC_SOURCES = {
    "BOJ_RELEASE_SCHEDULE": "https://www.boj.or.jp/en/about/calendar/index.htm",
    "JAPAN_STAT_CPI": "https://www.stat.go.jp/english/data/cpi/1582.html",
    "JAPAN_STAT_LABOUR_FORCE": "https://www.stat.go.jp/english/data/roudou/1543.html",
    "JAPAN_STAT_HOUSEHOLD_SPENDING": "https://www.stat.go.jp/english/data/kakei/1562.htm",
    "JAPAN_ESRI_GENERAL": "https://www.esri.cao.go.jp/en/stat/stat-schedule-e.html",
    "JAPAN_ESRI_GDP": "https://www.esri.cao.go.jp/en/sna/kouhyou/kouhyou_top.html",
    "US_BEA_RELEASE_SCHEDULE": "https://www.bea.gov/news/schedule",
}

def month_url(source_id: str, target: date) -> str:
    if source_id == "US_BLS_HIGH_IMPACT_SCHEDULE_COVERAGE":
        return f"https://www.bls.gov/schedule/{target.year}/{target.month:02d}_sched_list.htm"
    if source_id == "FEDERAL_RESERVE_CALENDAR":
        month = target.strftime("%B").lower()
        return f"https://www.federalreserve.gov/newsevents/{target.year}-{month}.htm"
    return STATIC_SOURCES[source_id]

def parse_dt(value: str) -> datetime:
    x = datetime.fromisoformat(str(value))
    if x.tzinfo is None:
        raise RuntimeError("request timestamp must be offset-aware")
    return x

def parse_date_text(text: str, default_year: int, default_month: int | None = None) -> date | None:
    s = " ".join(str(text).replace("\xa0", " ").split())
    if not s:
        return None
    s2 = s.replace(".", "")
    m = re.search(r"(?i)\b(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\s*[, ]?\s*(\d{1,2})(?:\s*,?\s*(\d{4}))?", s2)
    if m:
        mo = MONTHS[m.group(1).lower()]
        yr = int(m.group(3)) if m.group(3) else default_year
        return date(yr, mo, int(m.group(2)))
    if default_month is not None:
        m = re.fullmatch(r"\s*(\d{1,2})\s*", s)
        if m:
            return date(default_year, default_month, int(m.group(1)))
    return None

def parse_time_text(text: str) -> time | None:
    s = " ".join(str(text).lower().replace("\xa0", " ").split())
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?", s)
    if m:
        h = int(m.group(1)); minute = int(m.group(2) or 0)
        if m.group(3) == "p" and h != 12: h += 12
        if m.group(3) == "a" and h == 12: h = 0
        return time(h, minute)
    m = re.search(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)", s)
    if m:
        return time(int(m.group(1)), int(m.group(2)))
    return None

def localize(d: date, t: time | None, tz: ZoneInfo) -> str | None:
    if t is None:
        return None
    return datetime.combine(d, t, tzinfo=tz).astimezone(UTC).isoformat()

def event(source_id: str, title: str, d: date, t: time | None, tz: ZoneInfo, impact: str, url: str) -> dict:
    return {
        "source_id": source_id,
        "title": " ".join(title.split()),
        "event_date": d.isoformat(),
        "scheduled_time": t.isoformat(timespec="minutes") if t else None,
        "timezone": str(tz),
        "scheduled_at_utc": localize(d, t, tz),
        "time_precision": "EXACT_OR_PUBLISHED_APPROXIMATE" if t else "DATE_ONLY",
        "impact": impact,
        "reference": url,
    }

def classify_boj(title: str) -> str:
    s = title.lower()
    high = (
        "statement on monetary policy" in s
        or "outlook for economic activity and prices" in s
        or "monetary policy meeting" in s
        or "press conference" in s
        or ("speech by" in s and any(k in s for k in ["governor", "deputy governor", "board member"]))
    )
    return "HIGH" if high else "CONTEXT"

def parse_boj(html: str, target: date, url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = None
    for t in soup.find_all("table"):
        headers = [" ".join(x.stripped_strings) for x in t.find_all("th")]
        if {"Date", "Time", "Title"}.issubset(set(headers)):
            table = t
            break
    if table is None:
        raise RuntimeError("BOJ release schedule table not found")
    out=[]; carry_month=None; carry_date=None
    for tr in table.find_all("tr"):
        cells=[" ".join(x.stripped_strings) for x in tr.find_all(["td","th"])]
        if len(cells) < 3 or cells[0]=="Date":
            continue
        dtext,ttext,title=cells[0],cells[1],cells[2]
        if dtext:
            d=parse_date_text(dtext,target.year,carry_month)
            if d is not None:
                carry_date=d; carry_month=d.month
        d=carry_date
        if d is None:
            continue
        out.append(event("BOJ_RELEASE_SCHEDULE",title,d,parse_time_text(ttext),TOKYO,classify_boj(title),url))
    return out

def parse_stat_single_release(html: str, target: date, url: str, source_id: str, title: str) -> list[dict]:
    soup=BeautifulSoup(html,"html.parser")
    out=[]
    for tr in soup.find_all("tr"):
        cells=[" ".join(x.stripped_strings) for x in tr.find_all(["td","th"])]
        if len(cells) < 2:
            continue
        d=parse_date_text(cells[1],target.year)
        if d is None:
            continue
        out.append(event(source_id,title,d,None,TOKYO,"HIGH",url))
    if not out:
        raise RuntimeError(f"{source_id} release rows not found")
    return out

def parse_esri_general(html: str, target: date, url: str) -> list[dict]:
    soup=BeautifulSoup(html,"html.parser")
    table=None
    for t in soup.find_all("table"):
        rows=t.find_all("tr")
        if not rows: continue
        headers=[" ".join(x.stripped_strings) for x in rows[0].find_all(["td","th"])]
        if any("Machinery Orders" in h for h in headers):
            table=t; break
    if table is None:
        raise RuntimeError("ESRI general schedule table not found")
    rows=table.find_all("tr")
    headers=[" ".join(x.stripped_strings) for x in rows[0].find_all(["td","th"])]
    out=[]
    for tr in rows[1:]:
        cells=[" ".join(x.stripped_strings) for x in tr.find_all(["td","th"])]
        for i,text in enumerate(cells):
            if i>=len(headers): continue
            d=parse_date_text(text,target.year)
            if d is None: continue
            title=headers[i]
            impact="HIGH" if any(k in title for k in ["Machinery Orders","Business Outlook Survey"]) else "CONTEXT"
            out.append(event("JAPAN_ESRI_GENERAL",title,d,None,TOKYO,impact,url))
    return out

def parse_esri_gdp(html: str, target: date, url: str) -> list[dict]:
    soup=BeautifulSoup(html,"html.parser")
    out=[]
    for tr in soup.find_all("tr"):
        cells=[" ".join(x.stripped_strings) for x in tr.find_all(["td","th"])]
        if len(cells) < 3:
            continue
        d=parse_date_text(cells[1],target.year)
        if d is None:
            continue
        if "preliminary" not in cells[0].lower() and "quarter" not in cells[0].lower():
            continue
        out.append(event("JAPAN_ESRI_GDP",f"Quarterly Estimates of GDP: {cells[0]}",d,parse_time_text(cells[2]),TOKYO,"HIGH",url))
    if not out:
        raise RuntimeError("ESRI GDP schedule rows not found")
    return out

def parse_bea(html: str, target: date, url: str) -> list[dict]:
    soup=BeautifulSoup(html,"html.parser")
    out=[]
    for tr in soup.find_all("tr"):
        cells=[" ".join(x.stripped_strings) for x in tr.find_all(["td","th"])]
        if len(cells) < 3:
            continue
        d=parse_date_text(cells[0],target.year)
        if d is None:
            continue
        title=cells[-1]
        impact="HIGH" if ("GDP" in title or "Personal Income and Outlays" in title) else "CONTEXT"
        out.append(event("US_BEA_RELEASE_SCHEDULE",title,d,parse_time_text(cells[0]),EASTERN,impact,url))
    if not out:
        raise RuntimeError("BEA release schedule rows not found")
    return out

def parse_fed(html: str, target: date, url: str) -> list[dict]:
    soup=BeautifulSoup(html,"html.parser")
    root=soup.find("div",class_="cal-nojs")
    if root is None:
        raise RuntimeError("Federal Reserve no-JS calendar not found")
    out=[]
    for panel in root.find_all("div",class_=lambda c: c and "panel" in c.split()):
        title=" ".join(panel.stripped_strings)
        if not title:
            continue
        h4=panel.find_previous("h4")
        section=" ".join(h4.stripped_strings) if h4 else ""
        if section not in {"Speeches","FOMC Meetings"}:
            continue
        nums=[int(x) for x in re.findall(r"\b([1-9]|[12]\d|3[01])\b",title)]
        if not nums:
            continue
        d=date(target.year,target.month,nums[-1])
        t=parse_time_text(title)
        if section=="FOMC Meetings":
            impact="HIGH"
        else:
            low=title.lower()
            impact="HIGH" if any(k in low for k in [
                "economic outlook","monetary policy","inflation","interest rate","interest rates"
            ]) else "CONTEXT"
        out.append(event("FEDERAL_RESERVE_CALENDAR",f"{section}: {title}",d,t,EASTERN,impact,url))
    return out

def parse_bls(html: str, target: date, url: str) -> list[dict]:
    soup=BeautifulSoup(html,"html.parser")
    out=[]
    for tr in soup.find_all("tr"):
        cells=[" ".join(x.stripped_strings) for x in tr.find_all(["td","th"])]
        if len(cells) < 2:
            continue
        d=parse_date_text(cells[0],target.year)
        if d is None:
            continue
        joined=" | ".join(cells)
        title=cells[-1] if len(cells)>=3 else joined
        impact="HIGH" if any(k.lower() in joined.lower() for k in [
            "Employment Situation","Consumer Price Index","Producer Price Index"
        ]) else "CONTEXT"
        out.append(event("US_BLS_HIGH_IMPACT_SCHEDULE_COVERAGE",title,d,parse_time_text(joined),EASTERN,impact,url))
    if out:
        return out
    text="\n".join(" ".join(x.split()) for x in soup.stripped_strings)
    pat=re.compile(
        r"(?i)(Monday|Tuesday|Wednesday|Thursday|Friday),\s+"
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
        r"(\d{1,2}),\s+(\d{4})\s+(\d{1,2}:\d{2}\s+[AP]M)\s+([^\n]+)"
    )
    for m in pat.finditer(text):
        d=date(int(m.group(4)),MONTHS[m.group(2).lower()],int(m.group(3)))
        title=m.group(6)
        impact="HIGH" if any(k.lower() in title.lower() for k in [
            "Employment Situation","Consumer Price Index","Producer Price Index"
        ]) else "CONTEXT"
        out.append(event("US_BLS_HIGH_IMPACT_SCHEDULE_COVERAGE",title,d,parse_time_text(m.group(5)),EASTERN,impact,url))
    if not out:
        raise RuntimeError("BLS release schedule rows not found")
    return out

OMB_PFEI_2026_URL = "https://www.whitehouse.gov/wp-content/uploads/2025/09/pfei_schedule_release_dates_cy2026.pdf"
BLS_TIME_REFS = {
    "The Employment Situation": "https://www.bls.gov/schedule/news_release/empsit.htm",
    "Producer Price Indexes": "https://www.bls.gov/schedule/news_release/ppi.htm",
    "Consumer Price Index": "https://www.bls.gov/schedule/news_release/cpi.htm",
}

def _first_day_number(cell: str | None) -> int | None:
    if cell is None:
        return None
    for m in re.finditer(r"(?<!\d)([1-9]|[12]\d|3[01])(?!\d)", str(cell)):
        return int(m.group(1))
    return None

def parse_omb_pfei_bls_table(table: list[list], target: date, url: str) -> list[dict]:
    wanted={
        "The Employment Situation":"The Employment Situation",
        "Producer Price Indexes":"Producer Price Indexes",
        "Consumer Price Index":"Consumer Price Index",
    }
    out=[]
    month_col=1+target.month
    for row in table:
        if len(row)<=month_col:
            continue
        label=" ".join(str(row[1] or "").split())
        matched=None
        for needle,title in wanted.items():
            if needle in label:
                matched=title
                break
        if matched is None:
            continue
        day=_first_day_number(row[month_col])
        if day is None:
            raise RuntimeError(f"OMB PFEI date missing for {matched} {target.year}-{target.month:02d}")
        e=event(
            "US_BLS_HIGH_IMPACT_SCHEDULE_COVERAGE",
            matched,
            date(target.year,target.month,day),
            time(8,30),
            EASTERN,
            "HIGH",
            url,
        )
        e["schedule_date_source"]="OMB_PFEI_2026"
        e["schedule_time_source"]="BLS_BY_NEWS_RELEASE_FROZEN_08_30_ET"
        e["schedule_time_reference"]=BLS_TIME_REFS[matched]
        out.append(e)
    if len(out)!=3:
        raise RuntimeError(f"OMB PFEI expected 3 BLS high-impact rows, got {len(out)}")
    return out

def parse_omb_pfei_bls(pdf_bytes: bytes, target: date, url: str) -> list[dict]:
    if target.year != 2026:
        raise RuntimeError("OMB PFEI fallback currently frozen only for calendar year 2026")
    tables=[]
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                if any(
                    any("BUREAU OF LABOR STATISTICS" in str(cell or "") for cell in row)
                    for row in table
                ):
                    tables.append(table)
    if not tables:
        raise RuntimeError("OMB PFEI BLS table not found")
    return parse_omb_pfei_bls_table(tables[0],target,url)

PARSERS = {
    "BOJ_RELEASE_SCHEDULE": parse_boj,
    "JAPAN_STAT_CPI": lambda h,t,u: parse_stat_single_release(h,t,u,"JAPAN_STAT_CPI","National Consumer Price Index"),
    "JAPAN_STAT_LABOUR_FORCE": lambda h,t,u: parse_stat_single_release(h,t,u,"JAPAN_STAT_LABOUR_FORCE","Labour Force Survey basic tabulation"),
    "JAPAN_STAT_HOUSEHOLD_SPENDING": lambda h,t,u: parse_stat_single_release(h,t,u,"JAPAN_STAT_HOUSEHOLD_SPENDING","Family Income and Expenditure Survey monthly household spending"),
    "JAPAN_ESRI_GENERAL": parse_esri_general,
    "JAPAN_ESRI_GDP": parse_esri_gdp,
    "US_BLS_HIGH_IMPACT_SCHEDULE_COVERAGE": parse_bls,
    "US_BEA_RELEASE_SCHEDULE": parse_bea,
    "FEDERAL_RESERVE_CALENDAR": parse_fed,
}

def fetch_source(session: requests.Session, source_id: str, target: date, timeout: int, fixture_dir: Path | None):
    url=month_url(source_id,target)
    if fixture_dir is not None:
        fp=fixture_dir/f"{source_id}.html"
        if not fp.exists():
            raise RuntimeError(f"fixture missing: {fp}")
        content=fp.read_bytes()
        return url,200,content
    r=session.get(url,timeout=timeout)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}")
    return str(r.url),r.status_code,r.content

def fetch_bls_coverage(session: requests.Session, target: date, timeout: int, fixture_dir: Path | None):
    primary_url=month_url("US_BLS_HIGH_IMPACT_SCHEDULE_COVERAGE",target)
    primary_error=None
    try:
        if fixture_dir is not None:
            fp=fixture_dir/"US_BLS_HIGH_IMPACT_SCHEDULE_COVERAGE.html"
            if not fp.exists():
                raise RuntimeError(f"fixture missing: {fp}")
            content=fp.read_bytes()
            final_url=primary_url; status=200
        else:
            r=session.get(primary_url,timeout=timeout)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            content=r.content; final_url=str(r.url); status=r.status_code
        parsed=parse_bls(content.decode("utf-8",errors="replace"),target,final_url)
        return {
            "reference":final_url,
            "http_status":status,
            "content":content,
            "parsed":parsed,
            "transport_mode":"BLS_DIRECT_MONTHLY",
            "publisher":"U.S. Bureau of Labor Statistics",
            "primary_reference":primary_url,
            "primary_failure":None,
        }
    except Exception as exc:
        primary_error=str(exc)

    if target.year != 2026:
        raise RuntimeError(f"BLS direct failed ({primary_error}); OMB fallback not frozen for {target.year}")
    try:
        if fixture_dir is not None:
            fp=fixture_dir/"OMB_PFEI_2026.pdf"
            if not fp.exists():
                raise RuntimeError(f"fixture missing: {fp}")
            content=fp.read_bytes()
            final_url=OMB_PFEI_2026_URL; status=200
        else:
            r=session.get(OMB_PFEI_2026_URL,timeout=timeout)
            if r.status_code != 200:
                raise RuntimeError(f"OMB HTTP {r.status_code}")
            if "pdf" not in str(r.headers.get("content-type","")).lower():
                raise RuntimeError(f"OMB unexpected content-type {r.headers.get('content-type')}")
            content=r.content; final_url=str(r.url); status=r.status_code
        parsed=parse_omb_pfei_bls(content,target,final_url)
        return {
            "reference":final_url,
            "http_status":status,
            "content":content,
            "parsed":parsed,
            "transport_mode":"OMB_PFEI_FALLBACK",
            "publisher":"Executive Office of the President / Office of Management and Budget / OIRA",
            "primary_reference":primary_url,
            "primary_failure":primary_error,
        }
    except Exception as exc:
        raise RuntimeError(f"BLS direct failed ({primary_error}); OMB PFEI fallback failed ({exc})")

def evaluate_event_state(events: list[dict], failures: list[dict], evaluated_at: datetime, target: date):
    req_utc=evaluated_at.astimezone(UTC)
    close_utc=datetime.combine(target,time(15,45),tzinfo=TOKYO).astimezone(UTC)
    if req_utc >= close_utc:
        raise RuntimeError("event-state evaluation must occur before target OSE day-session close")
    future=[]; past=[]; ambiguous=[]
    req_tokyo=evaluated_at.astimezone(TOKYO)
    for e in events:
        if e.get("impact")!="HIGH":
            continue
        if e.get("scheduled_at_utc"):
            x=datetime.fromisoformat(e["scheduled_at_utc"]).astimezone(UTC)
            if req_utc < x <= close_utc:
                future.append(e)
            elif date.fromisoformat(e["event_date"])==target and x <= req_utc:
                past.append(e)
        else:
            ed=date.fromisoformat(e["event_date"])
            if ed==target:
                if req_tokyo.date() < target:
                    future.append(e)
                else:
                    ambiguous.append(e)
    if future:
        return "PRE_RELEASE_HIGH",future,past,ambiguous,None
    if ambiguous:
        reason="HIGH_IMPACT_DATE_ONLY_EVENT_TIME_UNRESOLVED"
        if failures:
            reason += "_AND_REQUIRED_SOURCE_FAILURE"
        return "UNKNOWN",future,past,ambiguous,reason
    if failures:
        return "UNKNOWN",future,past,ambiguous,"REQUIRED_OFFICIAL_EVENT_SOURCE_UNAVAILABLE_OR_PARSER_INVALID"
    if past:
        return "POST_EVENT_HIGH",future,past,ambiguous,None
    return "NORMAL",future,past,ambiguous,None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--target-day-session-date",required=True)
    ap.add_argument("--output",type=Path)
    ap.add_argument("--timeout-seconds",type=int,default=15)
    ap.add_argument("--fixture-dir",type=Path)
    ap.add_argument("--as-of-taipei",help="Selftest/fixture only. Live mode always uses actual completion time.")
    args=ap.parse_args()

    target=date.fromisoformat(args.target_day_session_date)
    if args.as_of_taipei and args.fixture_dir is None:
        raise RuntimeError("--as-of-taipei is permitted only with --fixture-dir")
    fixed_asof=parse_dt(args.as_of_taipei).astimezone(TAIPEI) if args.as_of_taipei else None

    protocol=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    required=list(protocol["required_sources"])
    session=requests.Session()
    session.headers.update({
        "User-Agent":"Mozilla/5.0 (compatible; JNU-Operational-Research/1.0)",
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    events=[]; failures=[]; source_records=[]
    for source_id in required:
        url=month_url(source_id,target)
        try:
            if source_id=="US_BLS_HIGH_IMPACT_SCHEDULE_COVERAGE":
                info=fetch_bls_coverage(session,target,args.timeout_seconds,args.fixture_dir)
                final_url=info["reference"]; status=info["http_status"]; content=info["content"]; parsed=info["parsed"]
                record_extra={
                    "transport_mode":info["transport_mode"],
                    "publisher":info["publisher"],
                    "primary_reference":info["primary_reference"],
                    "primary_failure":info["primary_failure"],
                }
            else:
                final_url,status,content=fetch_source(session,source_id,target,args.timeout_seconds,args.fixture_dir)
                text=content.decode("utf-8",errors="replace")
                parsed=PARSERS[source_id](text,target,final_url)
                record_extra={"transport_mode":"DIRECT_OFFICIAL_HTTP","publisher":source_id}
            events.extend(parsed)
            source_records.append({
                "source":source_id,
                "reference":final_url,
                "checked_at_taipei":(fixed_asof or datetime.now(TAIPEI)).isoformat(),
                "http_status":status,
                "content_sha256_raw":hashlib.sha256(content).hexdigest(),
                "parsed_event_count":len(parsed),
                **record_extra,
            })
        except Exception as exc:
            failures.append({"source_id":source_id,"reference":url,"error":str(exc)})

    evaluated_at=fixed_asof or datetime.now(TAIPEI)
    state,future,past,ambiguous,reason=evaluate_event_state(events,failures,evaluated_at,target)
    evidence={
        "checked_at_taipei":evaluated_at.isoformat(),
        "target_day_session_date":target.isoformat(),
        "event_state":state,
        "volatility_state":"UNKNOWN",
        "sq_state":"UNKNOWN",
        "event_sources":source_records,
    }
    if state=="UNKNOWN":
        evidence["event_unavailability_reason"]=reason or "UNKNOWN_EVENT_STATE"
    result={
        "version":"1.1",
        "status":"OFFICIAL_EVENT_STATE_READY" if state!="UNKNOWN" else "OFFICIAL_EVENT_STATE_FAIL_CLOSED_UNKNOWN",
        "protocol":"config/jnu_official_event_state_protocol_v1_1.json",
        "evaluated_at_taipei":evaluated_at.isoformat(),
        "target_day_session_date":target.isoformat(),
        "event_state":state,
        "risk_state_evidence":evidence,
        "future_high_events":future,
        "past_high_events":past,
        "ambiguous_date_only_high_events":ambiguous,
        "source_failures":failures,
        "all_parsed_events":[e for e in events if e["event_date"]==target.isoformat()],
        "decision_risk_modifiers":{
            "volatility_state":"UNKNOWN",
            "event_state":state,
            "sq_state":"UNKNOWN",
            "post_event_exact_jnu_path_available":False,
        },
        "real_registration_performed":False,
    }
    s=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(s+"\n",encoding="utf-8")
    print(s)
    raise SystemExit(0 if state!="UNKNOWN" else 3)

if __name__=="__main__":
    main()
