from __future__ import annotations
import csv, hashlib, io, json, zipfile
from datetime import date, datetime, time
from pathlib import Path
import pandas as pd

ROOT=Path(r"D:\JERRY_BACKTEST_CLOUD_SYNC_20260831")
RAW=Path(r"D:\QROS\data\personal_licensed\225labo\mini\raw")
FRED=Path(r"D:\Temp\nikkei225_2012_20260902.csv")
OUT=Path(r"D:\QROS\data\derived\jnu_basis_change_g1\ose_mini_cash_basis_change_signal_panel_v1.json")
SUMMARY=ROOT/"config"/"jnu_ose_mini_cash_basis_change_data_gate_v1.json"

def sha_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def cash_close_stamp(d:date)->str:
    return "15:30" if d>=date(2024,11,5) else "15:00"

def entry_stamp(d:date)->str:
    return "15:35" if d>=date(2024,11,5) else "15:05"

def read_5m_from_zip(zp:Path)->pd.DataFrame:
    with zipfile.ZipFile(zp) as z:
        names=z.namelist()
        if len(names)!=1:
            raise RuntimeError(f"{zp.name}: expected one workbook, got {len(names)}")
        b=z.read(names[0])
    raw=pd.read_excel(io.BytesIO(b),sheet_name="5min",header=None)
    header_idx=None
    for i in range(min(8,len(raw))):
        a=str(raw.iloc[i,0]); b=str(raw.iloc[i,1])
        if "日付" in a and "時間" in b:
            header_idx=i; break
    if header_idx is None:
        raise RuntimeError(f"{zp.name}: could not locate 5min header")
    df=raw.iloc[header_idx+1:,:7].copy()
    df.columns=["date","time","open","high","low","close","volume"]
    df["date"]=pd.to_datetime(df["date"],errors="coerce")
    df=df[df["date"].notna()].copy()
    def norm_time(v):
        if isinstance(v,time): return v.strftime("%H:%M")
        s=str(v)
        m=s[:5]
        return m
    df["hhmm"]=df["time"].map(norm_time)
    return df[["date","hhmm","open"]]

def second_friday(year:int,month:int)->date:
    d=date(year,month,1)
    while d.weekday()!=4: d=date.fromordinal(d.toordinal()+1)
    return date.fromordinal(d.toordinal()+7)

def main():
    prices={}
    valid_dates=[]
    with FRED.open(encoding="utf-8",newline="") as f:
        for r in csv.DictReader(f):
            v=(r.get("NIKKEI225") or "").strip()
            if v in {"",".","NA","NaN"}: continue
            d=date.fromisoformat(r["observation_date"])
            if d<date(2012,1,4): continue
            prices[d]=float(v)
            valid_dates.append(d)
    valid_dates=sorted(set(valid_dates))
    index={d:i for i,d in enumerate(valid_dates)}

    bar_open={}
    source_hashes={}
    duplicate_conflicts=[]
    for year in range(2012,2027):
        zp=RAW/f"N225minif_{year}.zip"
        if not zp.exists(): raise RuntimeError(f"missing {zp}")
        source_hashes[zp.name]=sha_file(zp)
        df=read_5m_from_zip(zp)
        for row in df.itertuples(index=False):
            dd=row.date.date(); hh=row.hhmm
            if hh not in {"15:00","15:05","15:30","15:35"}: continue
            try: op=float(row.open)
            except Exception: continue
            k=(dd,hh)
            if k in bar_open and abs(bar_open[k]-op)>1e-12:
                duplicate_conflicts.append({"date":dd.isoformat(),"time":hh,"a":bar_open[k],"b":op,"source":zp.name})
            else:
                bar_open[k]=op
    if duplicate_conflicts:
        raise RuntimeError(f"duplicate bar conflicts: {duplicate_conflicts[:5]}")

    # Roll-risk windows instantiated on the actual Nikkei valid trading calendar.
    excluded=set()
    sq_days=[]
    for y in range(2012,2027):
        for m in (3,6,9,12):
            nominal=second_friday(y,m)
            eligible=[d for d in valid_dates if d<=nominal]
            if not eligible: continue
            sq=eligible[-1]
            if sq not in index: continue
            i=index[sq]
            lo=max(0,i-10); hi=min(len(valid_dates)-1,i+2)
            win=valid_dates[lo:hi+1]
            excluded.update(win)
            sq_days.append({"year":y,"month":m,"nominal_second_friday":nominal.isoformat(),"sq_business_day":sq.isoformat(),"excluded_from":win[0].isoformat(),"excluded_to":win[-1].isoformat()})

    basis={}
    basis_missing=[]
    for d in valid_dates:
        if d>date(2026,8,31): continue
        hh=cash_close_stamp(d)
        k=(d,hh)
        if k not in bar_open:
            basis_missing.append({"date":d.isoformat(),"required_reference_time":hh})
            continue
        basis[d]=bar_open[k]-prices[d]

    records=[]
    incomplete=[]
    ordered=[d for d in valid_dates if d<=date(2026,8,31)]
    for i in range(1,len(ordered)-1):
        prev=ordered[i-1]; cur=ordered[i]; nxt=ordered[i+1]
        if any(x in excluded for x in (prev,cur,nxt)):
            continue
        if prev not in basis or cur not in basis:
            incomplete.append({"date":cur.isoformat(),"reason":"MISSING_CURRENT_OR_PREVIOUS_BASIS"})
            continue
        entry_hh=entry_stamp(cur)
        exit_hh=cash_close_stamp(nxt)
        if (cur,entry_hh) not in bar_open:
            incomplete.append({"date":cur.isoformat(),"reason":"MISSING_ENTRY_TIMESTAMP","time":entry_hh})
            continue
        if (nxt,exit_hh) not in bar_open:
            incomplete.append({"date":cur.isoformat(),"reason":"MISSING_EXIT_TIMESTAMP","exit_date":nxt.isoformat(),"time":exit_hh})
            continue
        db=basis[cur]-basis[prev]
        sign=1 if db>0 else (-1 if db<0 else 0)
        records.append({
            "signal_date":cur.isoformat(),
            "previous_cash_date":prev.isoformat(),
            "next_cash_date":nxt.isoformat(),
            "cash_close_time":cash_close_stamp(cur),
            "entry_time":entry_hh,
            "exit_time":exit_hh,
            "cash_close":prices[cur],
            "mini_reference_open":bar_open[(cur,cash_close_stamp(cur))],
            "basis_points":basis[cur],
            "previous_basis_points":basis[prev],
            "delta_basis_points":db,
            "signal_sign":sign,
            "entry_price_read":False,
            "exit_price_read":False,
        })
    n=len(records)
    sign_counts={"long":sum(r["signal_sign"]==1 for r in records),"short":sum(r["signal_sign"]==-1 for r in records),"flat":sum(r["signal_sign"]==0 for r in records)}
    gate={
        "formal_sample_start":"2012-01-04",
        "formal_sample_last_available_signal_date":records[-1]["signal_date"] if records else None,
        "fred_valid_cash_days_through_2026_08_31":sum(d<=date(2026,8,31) for d in valid_dates),
        "mini_cash_reference_days":len(basis),
        "basis_missing_days":len(basis_missing),
        "roll_excluded_unique_days":len(excluded),
        "complete_signal_alignment_records":n,
        "minimum_2500_observations_pass":n>=2500,
        "incomplete_nonroll_records":len(incomplete),
        "duplicate_bar_conflicts":len(duplicate_conflicts),
        "entry_exit_prices_read":False,
        "directional_outcomes_read":False,
        "signal_counts":sign_counts,
    }
    out={
        "version":"1.0",
        "candidate_id":"OSE_MINI_CASH_BASIS_CHANGE_G1",
        "status":"SIGNAL_PANEL_BUILT_NO_DIRECTIONAL_OUTCOMES",
        "fred_csv_sha256":sha_file(FRED),
        "mini_source_hashes":source_hashes,
        "roll_windows":sq_days,
        "gate":gate,
        "basis_missing_sample":basis_missing[:20],
        "incomplete_sample":incomplete[:20],
        "records":records,
        "directional_outcome_inspected":False,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    panel_sha=sha_file(OUT)
    summary={
        "version":"1.0",
        "candidate_id":"OSE_MINI_CASH_BASIS_CHANGE_G1",
        "status":"SOURCE_SIGNAL_ALIGNMENT_DATA_GATE_PASS" if (n>=2500 and not duplicate_conflicts and len(incomplete)==0) else "SOURCE_SIGNAL_ALIGNMENT_DATA_GATE_REVIEW_REQUIRED",
        "signal_panel_local_only":True,
        "signal_panel_sha256":panel_sha,
        "signal_panel_size_bytes":OUT.stat().st_size,
        "fred_csv_sha256":sha_file(FRED),
        "mini_source_file_count":len(source_hashes),
        "mini_source_hashes":source_hashes,
        "gate":gate,
        "directional_outcome_inspected":False,
        "next_action":"Freeze four chronological subperiod boundaries from signal-date records before reading entry/exit price values."
    }
    SUMMARY.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
