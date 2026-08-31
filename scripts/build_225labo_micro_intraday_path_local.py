#!/usr/bin/env python3
"""Local-only exact-product JNU intraday-path feature adapter.

Reads personally licensed 225Labo Nikkei 225 Micro annual 1-minute workbooks
from local storage and emits only non-reconstructive daily path features:
FIRST30, MIDDLE, LAST30 and day-session returns plus provenance/DQ metadata.

No raw minute bars are emitted or uploaded.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

EXPECTED_HEADER = ["日付","時間","始値","高値","安値","終値","出来高"]


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for b in iter(lambda: fh.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()


def load_calendar(path: Path) -> dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_hhmm(s: str) -> int:
    s=s.replace("+1","")
    hh,mm=map(int,s.split(":"))
    return hh*60+mm


def schedule_for(d: date, cal: dict[str,Any]) -> dict[str,Any]:
    ds=d.isoformat()
    for row in cal["ose_nikkei_index_futures"]:
        if ds < row["valid_from"]:
            continue
        if row["valid_to"] is not None and ds > row["valid_to"]:
            continue
        return row
    raise ValueError(f"no OSE session calendar for {ds}")


def normalize_date(v: Any) -> date:
    if isinstance(v,datetime):
        return v.date()
    if isinstance(v,date):
        return v
    text=str(v).strip().replace("/","-")
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return datetime.strptime(text.split()[0],"%Y-%m-%d").date()


def normalize_time(v: Any) -> time:
    if isinstance(v,datetime):
        return v.time().replace(microsecond=0)
    if isinstance(v,time):
        return v.replace(microsecond=0)
    if isinstance(v,(int,float)):
        seconds=round(float(v)*86400)%86400
        return time(seconds//3600,(seconds%3600)//60,seconds%60)
    return time.fromisoformat(str(v).strip()).replace(microsecond=0)


def minute_of_day(t: time) -> int:
    return t.hour*60+t.minute


def in_day_session(m: int, sched: dict[str,Any]) -> bool:
    for a,b in sched["day_session_segments"]:
        if parse_hhmm(a) <= m <= parse_hhmm(b):
            return True
    return False


def expected_active_minutes(sched: dict[str,Any]) -> list[int]:
    out=[]
    for a,b in sched["day_session_segments"]:
        aa,bb=parse_hhmm(a),parse_hhmm(b)
        # Match proxy G2 endpoint convention: include start minute, exclude close boundary.
        out.extend(range(aa,bb))
    return sorted(set(out))


def window_spec(sched: dict[str,Any]) -> dict[str,Any]:
    active=expected_active_minutes(sched)
    if len(active)<61:
        raise ValueError("day session too short for fixed FIRST/LAST30")
    start=min(active)
    close=max(active)+1
    first=set(m for m in active if start <= m < start+30)
    last=set(m for m in active if close-30 <= m < close)
    middle=set(active)-first-last
    return {
        "start":start,
        "close":close,
        "first":first,
        "middle":middle,
        "last":last,
        "expected_first":len(first),
        "expected_middle":len(middle),
        "expected_last":len(last),
    }


@dataclass
class DayBars:
    values: dict[int,float]
    duplicate_rows: int=0
    invalid_rows: int=0
    out_of_day_rows: int=0

    def __init__(self):
        self.values={}
        self.duplicate_rows=0
        self.invalid_rows=0
        self.out_of_day_rows=0


def workbook_from_zip(path: Path) -> tuple[str,bytes]:
    with zipfile.ZipFile(path) as zf:
        members=[i for i in zf.infolist() if not i.is_dir() and i.filename.lower().endswith(".xlsx")]
        if len(members)!=1:
            raise ValueError(f"{path.name}: expected exactly one xlsx workbook")
        info=members[0]
        return info.filename,zf.read(info)


def parse_source(path: Path, cal: dict[str,Any]) -> tuple[dict[date,DayBars],dict[str,Any]]:
    import openpyxl
    member,raw=workbook_from_zip(path)
    wb=openpyxl.load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
    try:
        ws=wb["1min"]
        it=ws.iter_rows(values_only=True)
        header=[str(x).strip() if x is not None else "" for x in list(next(it))[:7]]
        if header != EXPECTED_HEADER:
            raise ValueError(f"{path.name}/1min unexpected header: {header}")
        days:dict[date,DayBars]={}
        total=0
        dmin=None
        dmax=None
        for row in it:
            if not row or all(v in (None,"") for v in row):
                continue
            total+=1
            d=normalize_date(row[0])
            t=normalize_time(row[1])
            sched=schedule_for(d,cal)
            m=minute_of_day(t)
            day=days.setdefault(d,DayBars())
            if not in_day_session(m,sched):
                day.out_of_day_rows+=1
                continue
            try:
                o,h,l,c,vol=[float(row[i]) for i in range(2,7)]
            except Exception:
                day.invalid_rows+=1
                continue
            if not (o>0 and h>0 and l>0 and c>0 and vol>=0 and h>=max(o,c,l) and l<=min(o,c,h)):
                day.invalid_rows+=1
                continue
            if m in day.values:
                day.duplicate_rows+=1
                continue
            day.values[m]=c
            dmin=d if dmin is None or d<dmin else dmin
            dmax=d if dmax is None or d>dmax else dmax
        meta={
            "source_id":path.name,
            "workbook_member":member,
            "row_count_1m":total,
            "distinct_trading_dates":len(days),
            "date_min":dmin.isoformat() if dmin else None,
            "date_max":dmax.isoformat() if dmax else None,
            "duplicate_rows":sum(v.duplicate_rows for v in days.values()),
            "invalid_rows":sum(v.invalid_rows for v in days.values()),
            "out_of_day_session_rows":sum(v.out_of_day_rows for v in days.values()),
        }
        return days,meta
    finally:
        wb.close()


def window_return(day: DayBars, allowed:set[int], minimum:int) -> tuple[float|None,int]:
    pts=sorted((m,c) for m,c in day.values.items() if m in allowed)
    if len(pts)<minimum:
        return None,len(pts)
    return float(math.log(pts[-1][1]/pts[0][1])),len(pts)


def annual_files(folder:Path)->list[Path]:
    fs=sorted(folder.glob("N225microf_*.zip"))
    if not fs:
        raise SystemExit("no N225microf_*.zip files found")
    return fs


def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--input-dir",type=Path,required=True)
    ap.add_argument("--calendar",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,required=True)
    ap.add_argument("--parser-commit",required=True)
    ap.add_argument("--middle-coverage",type=float,default=0.80)
    args=ap.parse_args()
    if abs(args.middle_coverage-0.80)>1e-12:
        raise SystemExit("fail closed: middle coverage is frozen at 0.80")
    args.output_dir.mkdir(parents=True,exist_ok=True)
    cal=load_calendar(args.calendar)

    sources=[]
    candidates:dict[date,list[tuple[int,Path,DayBars]]]={}
    source_hash={}
    for p in annual_files(args.input_dir):
        m=re.search(r"(20\d{2})",p.name)
        nominal=int(m.group(1)) if m else -1
        days,meta=parse_source(p,cal)
        digest=sha256_file(p)
        source_hash[p.name]=digest
        sources.append({
            "source_id":p.name,
            "sha256":digest,
            "size_bytes":p.stat().st_size,
            "nominal_year":nominal,
            "meta_1m":meta,
        })
        for d,bars in days.items():
            candidates.setdefault(d,[]).append((nominal,p,bars))

    selected={}
    overlap_days=0
    for d,items in candidates.items():
        if len(items)>1:
            overlap_days+=1
        exact=[x for x in items if x[0]==d.year]
        choice=sorted(exact if exact else items,key=lambda x:(x[0],x[1].name),reverse=True)[0]
        selected[d]=choice

    rows=[]
    incomplete=[]
    critical=[]
    for d,(nominal,p,day) in sorted(selected.items()):
        sched=schedule_for(d,cal)
        spec=window_spec(sched)
        f_ret,f_n=window_return(day,spec["first"],25)
        l_ret,l_n=window_return(day,spec["last"],25)
        min_middle=math.ceil(spec["expected_middle"]*0.80)
        m_ret,m_n=window_return(day,spec["middle"],min_middle)
        active=set(spec["first"])|set(spec["middle"])|set(spec["last"])
        day_ret,day_n=window_return(day,active,max(2,math.ceil(len(active)*0.80)))
        if f_ret is None or l_ret is None or m_ret is None or day_ret is None:
            incomplete.append({
                "trading_date":d.isoformat(),
                "first_bars":f_n,
                "middle_bars":m_n,
                "last_bars":l_n,
                "day_bars":day_n,
                "expected_first":spec["expected_first"],
                "expected_middle":spec["expected_middle"],
                "expected_last":spec["expected_last"],
            })
            continue
        if day.invalid_rows:
            critical.append({"trading_date":d.isoformat(),"issue":"INVALID_OHLCV_ROWS","count":day.invalid_rows})
            continue
        rows.append({
            "trading_date":d.isoformat(),
            "first30_return":f_ret,
            "middle_return":m_ret,
            "last30_return":l_ret,
            "day_session_return":day_ret,
            "first30_bars":f_n,
            "middle_bars":m_n,
            "last30_bars":l_n,
            "day_session_bars":day_n,
            "middle_coverage_ratio":m_n/spec["expected_middle"] if spec["expected_middle"] else 0.0,
            "source_file_sha256":source_hash[p.name],
            "transform_version":"225LABO_JNU_MICRO_PATH_V1",
        })

    panel=args.output_dir/"jnu_225labo_micro_intraday_path_v1.csv"
    fields=[
        "trading_date","first30_return","middle_return","last30_return","day_session_return",
        "first30_bars","middle_bars","last30_bars","day_session_bars","middle_coverage_ratio",
        "source_file_sha256","transform_version"
    ]
    with panel.open("w",encoding="utf-8",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=fields,lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    years=sorted({s["nominal_year"] for s in sources if s["nominal_year"]>0})
    manifest={
        "version":"1.0",
        "candidate_id":"INTRADAY_PATH_US_TO_JNU_TRUE_G1",
        "source_license_classification":"225LABO_PERSONAL_USE_LOCAL_RAW_DERIVED_NON_RECONSTRUCTIVE_EXPORT",
        "raw_data_cloud_uploaded":False,
        "parser_version_commit":args.parser_commit,
        "calendar_session_version":cal.get("version"),
        "source_hashes":[{"source_id":s["source_id"],"sha256":s["sha256"]} for s in sources],
        "product_contract_coverage":{
            "venue":"OSE",
            "product":"Nikkei 225 Micro Futures (JNU)",
            "years_present":years,
            "date_range":[rows[0]["trading_date"] if rows else None,rows[-1]["trading_date"] if rows else None],
        },
        "window_definitions":{
            "FIRST_30M":"historical OSE day open inclusive to open+30 exclusive",
            "LAST_30M":"historical OSE day close-30 inclusive to close exclusive",
            "MIDDLE":"active day-session minutes excluding FIRST30 and LAST30",
            "return":"log(last close / first close) within each state",
            "min_first_bars":25,
            "min_last_bars":25,
            "middle_coverage_fraction":0.80,
        },
        "selected_trading_days":len(rows),
        "incomplete_window_days_count":len(incomplete),
        "incomplete_window_days":incomplete[:100],
        "duplicate_summary":{
            "overlap_trading_days_across_annual_packages":overlap_days,
            "source_duplicate_rows":sum(s["meta_1m"]["duplicate_rows"] for s in sources),
        },
        "critical_data_quality_issues":critical,
        "derived_output_hash":sha256_file(panel),
        "derived_feature_definitions":{
            "first30_return":"fixed first 30 elapsed active day-session minutes",
            "middle_return":"active day-session minutes between fixed first/last windows",
            "last30_return":"fixed final 30 elapsed active day-session minutes",
            "day_session_return":"full eligible day-session return excluding close-boundary auction timestamp",
        },
        "sources":sources,
    }
    mpath=args.output_dir/"jnu_225labo_micro_intraday_path_v1_manifest.json"
    mpath.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":"DERIVED_PANEL_BUILT" if not critical else "DERIVED_PANEL_BUILT_WITH_CRITICAL_DQ",
        "rows":len(rows),
        "date_range":manifest["product_contract_coverage"]["date_range"],
        "incomplete_days":len(incomplete),
        "critical_issue_count":len(critical),
        "derived_output_hash":manifest["derived_output_hash"],
        "panel":str(panel),
        "manifest":str(mpath),
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
