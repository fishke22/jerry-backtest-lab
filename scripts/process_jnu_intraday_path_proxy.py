from __future__ import annotations

import gzip
import hashlib
import io
import json
import time
import traceback
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
REQUESTS=ROOT/"intraday_path_requests"
RESULTS=ROOT/"intraday_path_results"
REPORTS=ROOT/"intraday_path_reports"
DERIVED=ROOT/"cloud_data"/"derived"
MANIFESTS=ROOT/"cloud_data"/"manifests"
CACHE=ROOT/".cache"/"market-data"

UPSTREAM_REPO="FutureSharks/financial-data"
UPSTREAM_COMMIT="7ba1d404aa8b0e1c0f71321acebadcbfb9bcca8d"
EST_FIXED=timezone(timedelta(hours=-5))

BLOBS={
"JPXJPY":{
2011:"e62e4972f44b407a42ac297aa8beba371e9b32d3",
2012:"9b50dfb2f8ff8506e0f4f906268e27e67cc0aa12",
2013:"f1c9f34c04a6dca149a8352c9cc593816ad07d56",
2014:"a0dc8404dada354e28c930b439261d56213d00fe",
2015:"787f22e8f151922a8a8b3e3e15032961a86c00e1",
2016:"264688c4ba87c7cd76d1085324c99783db7aae29",
2017:"dd2c091c3e265e6a796d5e987049c8802d3e20aa",
2018:"0ea58be2dfa7910973fbed52831739edc3c07a60"},
"SPXUSD":{
2011:"f06834ef5dba9a3842807ce19375a5abbe429bad",
2012:"5d6c0c1dbe82dc9bff9a651bb3a573ae417bffde",
2013:"063c7e2cfb27d924f78be10424bcadc1aabf5c14",
2014:"b1f27b5228eb689423984d1bdccafe47dba47c81",
2015:"86c8125a6376fecda56629375bddace6eae9edbe",
2016:"f7eca59f0402a93ac06bf29a4f116ac372659963",
2017:"0299150334037188749a953d1e7147f2a7153d60",
2018:"85d1d96a1fea752bbebfc17b0fa2a23f14f0a911"}}

def sha256(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()

def raw_url(symbol:str,year:int)->str:
    return f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}/pyfinancialdata/data/stocks/histdata/{symbol}/DAT_ASCII_{symbol}_M1_{year}.csv"

def fetch(symbol:str,year:int,force:bool=False)->tuple[bytes,bool,str]:
    CACHE.mkdir(parents=True,exist_ok=True)
    p=CACHE/f"{symbol.lower()}_m1_{year}_{UPSTREAM_COMMIT[:12]}.csv"
    url=raw_url(symbol,year)
    if p.exists() and not force:
        return p.read_bytes(),True,url
    last=None
    for attempt in range(4):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 JerryBacktestLab/IntradayPathG0","Accept":"text/plain,text/csv,*/*;q=0.8"})
            with urllib.request.urlopen(req,timeout=180) as r:
                raw=r.read()
            p.write_bytes(raw)
            return raw,False,url
        except Exception as exc:
            last=exc
            if attempt<3: time.sleep(2**attempt)
    raise RuntimeError(f"fetch failed {symbol} {year}: {last}")

def parse_minutes(raw:bytes,target_tz:str)->pd.DataFrame:
    names=["stamp","open","high","low","close","volume"]
    df=pd.read_csv(io.BytesIO(raw),sep=";",header=None,names=names,usecols=range(6),dtype={"stamp":"string"})
    naive=pd.to_datetime(df["stamp"],format="%Y%m%d %H%M%S",errors="coerce")
    ok=naive.notna()
    df=df.loc[ok].copy()
    idx=pd.DatetimeIndex(naive.loc[ok]).tz_localize(EST_FIXED).tz_convert(target_tz)
    df.index=idx
    for c in ["open","high","low","close"]:
        df[c]=pd.to_numeric(df[c],errors="coerce")
    return df.dropna(subset=["open","close"]).sort_index()

def japan_daily_path(df:pd.DataFrame)->pd.DataFrame:
    mins=df.index.hour*60+df.index.minute
    dates=pd.DatetimeIndex(df.index.tz_localize(None)).normalize()
    am_end=np.where(dates<pd.Timestamp("2011-11-21"),11*60,11*60+30)
    cash=((mins>=9*60)&(mins<am_end))|((mins>=12*60+30)&(mins<15*60))
    x=df.loc[cash,["open","close"]].copy()
    x["trade_date"]=pd.Index(x.index.date)
    rows=[]
    for date,g in x.groupby("trade_date",sort=True):
        g=g.sort_index()
        m=g.index.hour*60+g.index.minute
        first=g[(m>=9*60)&(m<9*60+30)]
        if len(first)<20: continue
        close_min=15*60
        last=g[(m>=close_min-30)&(m<close_min)]
        if len(last)<20: continue
        first_ret=float(np.log(first["close"].iloc[-1]/first["open"].iloc[0]))
        last_ret=float(np.log(last["close"].iloc[-1]/last["open"].iloc[0]))
        open_ts=g.index.min().tz_convert("UTC")
        rows.append({
            "japan_date":pd.Timestamp(date),
            "japan_open_utc":open_ts,
            "first30_ret":first_ret,
            "last30_ret":last_ret,
            "n_first30":int(len(first)),
            "n_last30":int(len(last)),
        })
    if not rows: return pd.DataFrame()
    return pd.DataFrame(rows).set_index("japan_date").sort_index()

def us_daily_returns(df:pd.DataFrame)->pd.DataFrame:
    mins=df.index.hour*60+df.index.minute
    cash=(mins>=9*60+30)&(mins<16*60)
    x=df.loc[cash,["open","close"]].copy()
    x["us_date"]=pd.Index(x.index.date)
    rows=[]
    for date,g in x.groupby("us_date",sort=True):
        g=g.sort_index()
        if len(g)<250: continue
        ret=float(np.log(g["close"].iloc[-1]/g["open"].iloc[0]))
        rows.append({
            "us_date":pd.Timestamp(date),
            "us_close_utc":g.index.max().tz_convert("UTC"),
            "us_cash_ret":ret,
            "n_us_minutes":int(len(g)),
        })
    if not rows: return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("us_close_utc")

def build_panel(req:dict)->tuple[pd.DataFrame,dict]:
    jp_parts=[]; us_parts=[]; sources={}
    force=bool(req.get("force_refresh",False))
    for symbol in ["JPXJPY","SPXUSD"]:
        for year in req["years"]:
            year=int(year)
            raw,hit,url=fetch(symbol,year,force)
            sources[f"{symbol}_{year}"]={
                "symbol":symbol,"year":year,"url":url,
                "upstream_commit":UPSTREAM_COMMIT,
                "git_blob_sha":BLOBS[symbol][year],
                "sha256":sha256(raw),"cache_hit":bool(hit),
                "raw_storage":"PINNED_UPSTREAM + ACTIONS_CACHE"
            }
            if symbol=="JPXJPY":
                jp_parts.append(japan_daily_path(parse_minutes(raw,"Asia/Tokyo")))
            else:
                us_parts.append(us_daily_returns(parse_minutes(raw,"America/New_York")))
    jp=pd.concat([x for x in jp_parts if len(x)]).sort_index()
    jp=jp[~jp.index.duplicated(keep="last")]
    us=pd.concat([x for x in us_parts if len(x)]).sort_values("us_close_utc")
    us=us.drop_duplicates("us_close_utc",keep="last")

    left=jp.reset_index().sort_values("japan_open_utc")
    merged=pd.merge_asof(
        left,us[["us_close_utc","us_date","us_cash_ret","n_us_minutes"]].sort_values("us_close_utc"),
        left_on="japan_open_utc",right_on="us_close_utc",
        direction="backward",allow_exact_matches=False
    )
    merged=merged.dropna(subset=["us_cash_ret"]).set_index("japan_date").sort_index()
    merged["us_to_japan_gap_hours"]=(merged["japan_open_utc"]-merged["us_close_utc"]).dt.total_seconds()/3600.0
    # Sanity: completed U.S. session must precede Japan open.
    merged=merged[merged["us_to_japan_gap_hours"]>0].copy()
    return merged,sources

def expanding_test(d:pd.DataFrame,target:str,expected_sign:int,min_train:int)->dict:
    z=d[[target,"us_cash_ret"]].copy()
    z["lag_target"]=z[target].shift(1)
    z=z.dropna()
    records=[]
    for i in range(min_train,len(z)):
        tr=z.iloc[:i]
        row=z.iloc[i]
        X0=np.column_stack([np.ones(len(tr)),tr["lag_target"].to_numpy(float)])
        X1=np.column_stack([np.ones(len(tr)),tr["lag_target"].to_numpy(float),tr["us_cash_ret"].to_numpy(float)])
        y=tr[target].to_numpy(float)
        b0=np.linalg.lstsq(X0,y,rcond=None)[0]
        b1=np.linalg.lstsq(X1,y,rcond=None)[0]
        p0=float(np.array([1.0,row["lag_target"]])@b0)
        p1=float(np.array([1.0,row["lag_target"],row["us_cash_ret"]])@b1)
        records.append({
            "date":z.index[i],"y":float(row[target]),"base":p0,"full":p1,
            "beta_us":float(b1[2])
        })
    o=pd.DataFrame(records).set_index("date")
    loss0=(o.y-o.base)**2
    loss1=(o.y-o.full)**2
    diff=loss0-loss1
    hit0=float((np.sign(o.base)==np.sign(o.y)).mean())
    hit1=float((np.sign(o.full)==np.sign(o.y)).mean())
    recent=o.loc["2015-01-01":"2018-12-31"]
    return {
        "oos":o,"loss_diff":diff,
        "summary":{
            "n":int(len(o)),
            "oos_from":str(o.index.min().date()),
            "oos_to":str(o.index.max().date()),
            "mse_base":float(loss0.mean()),
            "mse_full":float(loss1.mean()),
            "mse_improvement":float(diff.mean()),
            "hit_base":hit0,"hit_full":hit1,"hit_delta_pp":float((hit1-hit0)*100),
            "mean_beta_us":float(o.beta_us.mean()),
            "median_beta_us":float(o.beta_us.median()),
            "fraction_beta_expected_sign":float((np.sign(o.beta_us)==expected_sign).mean()),
            "recent_mean_beta_us":float(recent.beta_us.mean()) if len(recent) else None,
            "expected_sign":int(expected_sign),
        }
    }

def block_bootstrap(values:pd.Series,block:int,samples:int,seed:int)->dict:
    x=values.dropna().to_numpy(float); n=len(x)
    if n<30:return {"n":n,"mean":float(np.mean(x)) if n else 0.0,"ci95":[0.0,0.0],"prob_positive":0.0}
    block=max(1,min(block,n)); starts=np.arange(0,n-block+1); rng=np.random.default_rng(seed)
    means=np.empty(samples)
    for i in range(samples):
        acc=[]
        while len(acc)<n:
            s=int(rng.choice(starts)); acc.extend(x[s:s+block])
        means[i]=float(np.mean(acc[:n]))
    lo,hi=np.quantile(means,[0.025,0.975])
    return {"n":n,"mean":float(np.mean(x)),"ci95":[float(lo),float(hi)],"prob_positive":float(np.mean(means>0))}

def evaluate(panel:pd.DataFrame,req:dict)->dict:
    cfg=req["bootstrap"]; gate=float(req["pass_rules"]["min_bootstrap_prob_positive"])
    out={}
    family_pass=True
    for target,sign in [("first30_ret",-1),("last30_ret",1)]:
        t=expanding_test(panel,target,sign,int(req["minimum_training_days"]))
        s=t["summary"]
        b=block_bootstrap(t["loss_diff"],int(cfg["block_days"]),int(cfg["samples"]),int(cfg["seed"]))
        s["mse_improvement_bootstrap"]=b
        sign_ok=(np.sign(s["mean_beta_us"])==sign)
        recent_ok=(s["recent_mean_beta_us"] is not None and np.sign(s["recent_mean_beta_us"])==sign)
        passed=(s["mse_improvement"]>0 and b["prob_positive"]>=gate and sign_ok and recent_ok)
        s["pass_proxy_target"]=bool(passed)
        out[target]=s
        family_pass=family_pass and passed
    return {"targets":out,"family_pass":bool(family_pass)}

def report(result:dict)->str:
    lines=[
        f"# JNU Intraday Path Proxy G0 — {result['request_id']}","",
        f"- Status: **{result['promotion_status']}**",
        f"- Derived panel days: {result['panel_days']}",
        f"- Family PASS: **{result['evaluation']['family_pass']}**","",
        "## Frozen target tests"
    ]
    for target,s in result["evaluation"]["targets"].items():
        lines.append(
            f"- {target}: beta_US={s['mean_beta_us']:.8g}, expected={s['expected_sign']:+d}, "
            f"MSE Δ={s['mse_improvement']:.8g}, Pboot>0={s['mse_improvement_bootstrap']['prob_positive']:.3f}, "
            f"hit Δ={s['hit_delta_pp']:.3f}pp, recent beta={s['recent_mean_beta_us']:.8g}, PASS={s['pass_proxy_target']}"
        )
    lines += ["","## Guardrails",
        "- This is an index-proxy methodology screen, not JNU/OSE validation.",
        "- The prior U.S. session is selected strictly by completion timestamp before Japan open.",
        "- FIRST/LAST 30-minute windows are frozen from the 2026 direct Nikkei-futures evidence.",
        "- No window, predictor, or sign may be changed to rescue a failure on this sample.",""
    ]
    return "\n".join(lines)

def process(path:Path)->None:
    req=json.loads(path.read_text(encoding="utf-8")); rid=path.stem
    if req.get("request_id")!=rid: raise ValueError("request_id must match filename")
    RESULTS.mkdir(exist_ok=True); REPORTS.mkdir(exist_ok=True); DERIVED.mkdir(parents=True,exist_ok=True); MANIFESTS.mkdir(parents=True,exist_ok=True)
    outj=RESULTS/f"{rid}.json"; outm=REPORTS/f"{rid}.md"
    if outj.exists(): print(f"skip {rid}: result exists"); return
    panel,sources=build_panel(req)
    ev=evaluate(panel,req)
    durable=panel[["us_date","us_cash_ret","first30_ret","last30_ret","n_first30","n_last30","n_us_minutes","us_to_japan_gap_hours"]].copy()
    raw=gzip.compress(durable.to_csv(index=True).encode("utf-8"),compresslevel=9)
    datap=DERIVED/f"{rid}_panel.csv.gz"; datap.write_bytes(raw); dsha=sha256(raw)
    manifest={
      "dataset_id":"NIKKEI_SPX_INTRADAY_PATH_PROXY_2011_2018_G0",
      "status":"DURABLE_DERIVED_PROXY_DATASET","sources":sources,
      "source_commit":UPSTREAM_COMMIT,
      "time_integrity":{
        "raw_timezone":"fixed EST UTC-5 no DST",
        "japan_timezone":"Asia/Tokyo","us_timezone":"America/New_York",
        "japan_calendar":"config/jnu_session_calendar_versions.json",
        "availability_rule":"most recent fully completed U.S. cash session strictly before Japan open"
      },
      "path":str(datap.relative_to(ROOT)).replace("\\","/"),"sha256":dsha,
      "raw_storage_policy":"Pinned upstream plus Actions cache only; durable private output is derived daily path panel/provenance.",
      "formal_jnu_validation":"PROHIBITED_WITH_PROXY",
      "generated_at_utc":datetime.now(timezone.utc).isoformat()
    }
    manp=MANIFESTS/f"{rid}_panel.json"; manp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    result={
      "request_id":rid,"candidate_id":"INTRADAY_PATH_US_NIKKEI_PROXY_G0",
      "status":"complete","promotion_status":"PROXY_METHOD_SCREEN_ONLY",
      "preregistration":req["preregistration"],"panel_days":int(len(panel)),
      "derived_dataset":str(datap.relative_to(ROOT)).replace("\\","/"),"derived_sha256":dsha,
      "manifest":str(manp.relative_to(ROOT)).replace("\\","/"),
      "evaluation":ev,"generated_at_utc":datetime.now(timezone.utc).isoformat()
    }
    outj.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    outm.write_text(report(result),encoding="utf-8")
    print(f"completed {rid}")

def main()->int:
    REQUESTS.mkdir(exist_ok=True); failures=[]
    for p in sorted(REQUESTS.glob("*.json")):
        try: process(p)
        except Exception as exc:
            failures.append((p.name,str(exc))); traceback.print_exc()
    if failures:
        print(json.dumps({"failures":failures},ensure_ascii=False)); return 1
    return 0

if __name__=="__main__":
    raise SystemExit(main())
