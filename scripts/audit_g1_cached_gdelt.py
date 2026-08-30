from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/".cache"/"market-data"
OUT=ROOT/"workflow_diagnostics"/"g1_cache_structure_audit.json"

def parse_points(obj):
    pts=[]
    def walk(x):
        if isinstance(x,dict):
            lower={str(k).lower():k for k in x}
            if "date" in lower and "value" in lower:
                dt=pd.to_datetime(x[lower["date"]],errors="coerce",utc=True)
                if pd.notna(dt):
                    pts.append(dt.tz_convert(None).normalize())
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(obj)
    return pd.DatetimeIndex(pts)

def main():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    rows=[]
    files=sorted(CACHE.glob("g1_*.json"))
    for p in files:
        try:
            obj=json.loads(p.read_text(encoding="utf-8-sig",errors="replace"))
            idx=parse_points(obj)
            unique=pd.DatetimeIndex(sorted(set(idx)))
            if len(unique):
                full=pd.date_range(unique.min(),unique.max(),freq="D")
                missing=full.difference(unique)
                rows.append({
                    "file":p.name,
                    "points_total":int(len(idx)),
                    "dates_unique":int(len(unique)),
                    "duplicate_date_points":int(len(idx)-len(unique)),
                    "date_min":str(unique.min().date()),
                    "date_max":str(unique.max().date()),
                    "calendar_span_days":int(len(full)),
                    "missing_calendar_days":int(len(missing)),
                    "missing_examples":[str(x.date()) for x in missing[:10]],
                    "daily_grid_complete_within_returned_span":bool(len(missing)==0),
                })
            else:
                rows.append({"file":p.name,"points_total":0,"dates_unique":0})
        except Exception as e:
            rows.append({"file":p.name,"parse_error":str(e)})
    payload={
        "audit":"G1 cached GDELT structure only; no network and no model evaluation",
        "cache_dir":str(CACHE),
        "files_found":len(files),
        "files":rows,
        "interpretation_rule":"This audit only establishes whether successful cached Timeline JSON contains a contiguous daily grid within its returned span. It does not infer missing-day semantics from documentation.",
    }
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(payload,ensure_ascii=False,indent=2))
    return 0 if files else 2

if __name__=="__main__":
    raise SystemExit(main())
