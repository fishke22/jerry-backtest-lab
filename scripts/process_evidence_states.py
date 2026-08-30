from __future__ import annotations

import io
import json
import math
import time
import traceback
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REQUESTS = ROOT / "evidence_requests"
RESULTS = ROOT / "evidence_results"
REPORTS = ROOT / "evidence_reports"
CACHE = ROOT / ".cache" / "market-data"

FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={start}&coed={end}"


def fetch_cached(url: str, name: str, force: bool) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if path.exists() and not force:
        return path.read_bytes()
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 JerryBacktestLab/0.4"})
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            path.write_bytes(raw)
            return raw
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"fetch failed {name}: {last}")


def parse_nikkei(raw: bytes) -> pd.Series:
    df = pd.read_csv(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
    idx = pd.to_datetime(df.iloc[:,0], errors="coerce")
    val = pd.to_numeric(df.iloc[:,1], errors="coerce")
    s = pd.Series(val.to_numpy(), index=idx, name="nikkei").dropna().sort_index()
    return s[~s.index.duplicated(keep="last")]


def parse_fred(raw: bytes, series: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
    date_col = "DATE" if "DATE" in df.columns else ("observation_date" if "observation_date" in df.columns else df.columns[0])
    value_col = series if series in df.columns else df.columns[-1]
    idx = pd.to_datetime(df[date_col], errors="coerce")
    val = pd.to_numeric(df[value_col], errors="coerce")
    s = pd.Series(val.to_numpy(), index=idx, name=series).dropna().sort_index()
    return s[~s.index.duplicated(keep="last")]


def asof_strict(target_index: pd.DatetimeIndex, source: pd.Series) -> pd.Series:
    left = pd.DataFrame({"target": target_index}).sort_values("target")
    right = source.rename("value").reset_index()
    right.columns = ["source_date","value"]
    right = right.sort_values("source_date")
    merged = pd.merge_asof(
        left, right,
        left_on="target", right_on="source_date",
        direction="backward", allow_exact_matches=False
    )
    return pd.Series(merged["value"].to_numpy(), index=target_index, name=source.name)


def ols_predict_expanding(X: pd.DataFrame, y: pd.Series, start: int, positive: bool=False) -> pd.Series:
    pred = pd.Series(np.nan, index=y.index, dtype=float)
    for i in range(start, len(y)):
        train = pd.concat([X.iloc[:i], y.iloc[:i].rename("y")], axis=1).dropna()
        row = X.iloc[i]
        if len(train) < max(60, X.shape[1] * 10) or row.isna().any():
            continue
        A = np.column_stack([np.ones(len(train)), train[X.columns].to_numpy(dtype=float)])
        b = train["y"].to_numpy(dtype=float)
        beta, *_ = np.linalg.lstsq(A, b, rcond=None)
        p = float(np.r_[1.0, row.to_numpy(dtype=float)] @ beta)
        pred.iloc[i] = max(p, 1e-10) if positive else p
    return pred


def qlike(actual_var: pd.Series, pred_var: pd.Series) -> pd.Series:
    a,p = actual_var.align(pred_var, join="inner")
    p = p.clip(lower=1e-10)
    a = a.clip(lower=1e-12)
    return a / p + np.log(p)


def mse(actual: pd.Series, pred: pd.Series) -> pd.Series:
    a,p = actual.align(pred, join="inner")
    return (a-p)**2


def block_bootstrap_mean_ci(values: pd.Series, block: int, samples: int, seed: int) -> dict:
    x = values.dropna().to_numpy(dtype=float)
    n=len(x)
    if n < 30:
        return {"mean":float(np.mean(x)) if n else 0.0,"ci95":[0.0,0.0],"prob_positive":0.0}
    block=max(1,min(block,n))
    rng=np.random.default_rng(seed)
    starts=np.arange(0,n-block+1)
    means=[]
    for _ in range(samples):
        out=[]
        while len(out)<n:
            s=int(rng.choice(starts)); out.extend(x[s:s+block])
        means.append(float(np.mean(out[:n])))
    lo,hi=np.quantile(means,[0.025,0.975])
    return {"mean":float(np.mean(x)),"ci95":[float(lo),float(hi)],"prob_positive":float(np.mean(np.array(means)>0))}


def load(request: dict):
    suite=json.loads((ROOT/request["source_suite_result"]).read_text(encoding="utf-8"))
    src=suite["data"]["sources"]
    nk_path=CACHE/"nikkei_futures_daily.csv"
    if nk_path.exists():
        nk_raw=nk_path.read_bytes()
    else:
        nk_raw=fetch_cached(src["nikkei_futures"]["url"],"nikkei_futures_daily.csv",bool(request.get("force_refresh")))
    close=parse_nikkei(nk_raw).loc[request["date_from"]:request["date_to"]]
    start=(pd.Timestamp(request["date_from"])-pd.Timedelta(days=500)).date().isoformat()
    end=pd.Timestamp(request["date_to"]).date().isoformat()
    vix=parse_fred(fetch_cached(FRED.format(series="VIXCLS",start=start,end=end),"fred_vixcls.csv",bool(request.get("force_refresh"))),"VIXCLS")
    fx=parse_fred(fetch_cached(FRED.format(series="DEXJPUS",start=start,end=end),"fred_dexjpus.csv",bool(request.get("force_refresh"))),"DEXJPUS")
    return close,vix,fx


def volatility_test(close: pd.Series, request: dict) -> dict:
    r=close.pct_change()
    var=r.pow(2)
    cfg=request["volatility_state"]
    baseline=var.shift(1).rolling(int(cfg["baseline_window"])).mean()

    X=pd.DataFrame(index=close.index)
    X["rv1"]=var.shift(1)
    X["rvw"]=var.shift(1).rolling(int(cfg["har_week"])).mean()
    X["rvm"]=var.shift(1).rolling(int(cfg["har_month"])).mean()
    har=ols_predict_expanding(X,var,int(request["oos_start_days"]),positive=True)

    Xa=X.copy()
    lagret=r.shift(1)
    Xa["negshock"]=np.where(lagret<0, lagret.pow(2), 0.0)
    ahar=ols_predict_expanding(Xa,var,int(request["oos_start_days"]),positive=True)

    valid=pd.DataFrame({"actual":var,"baseline":baseline,"har":har,"ahar":ahar}).dropna()
    losses={}
    for name in ["baseline","har","ahar"]:
        losses[name]={
            "qlike":float(qlike(valid["actual"],valid[name]).mean()),
            "mse":float(mse(valid["actual"],valid[name]).mean())
        }
    best=min(["har","ahar"], key=lambda n: losses[n]["qlike"])
    recent=valid.tail(int(request["recent_days"]))
    recent_loss={
        n:{"qlike":float(qlike(recent["actual"],recent[n]).mean()),"mse":float(mse(recent["actual"],recent[n]).mean())}
        for n in ["baseline","har","ahar"]
    }
    qdiff=qlike(valid["actual"],valid["baseline"])-qlike(valid["actual"],valid[best])
    mdiff=mse(valid["actual"],valid["baseline"])-mse(valid["actual"],valid[best])
    boot=request["bootstrap"]
    return {
      "best_model":best,
      "oos_days":len(valid),
      "losses":losses,
      "recent_losses":recent_loss,
      "qlike_improvement_vs_baseline":float(losses["baseline"]["qlike"]-losses[best]["qlike"]),
      "mse_improvement_vs_baseline":float(losses["baseline"]["mse"]-losses[best]["mse"]),
      "qlike_improvement_bootstrap":block_bootstrap_mean_ci(qdiff,int(boot["block_days"]),int(boot["samples"]),int(boot["seed"])),
      "mse_improvement_bootstrap":block_bootstrap_mean_ci(mdiff,int(boot["block_days"]),int(boot["samples"]),int(boot["seed"])),
      "pass_state":bool(losses[best]["qlike"]<losses["baseline"]["qlike"] and losses[best]["mse"]<losses["baseline"]["mse"])
    }


def tail_risk_proxy_test(close: pd.Series, vix: pd.Series, request: dict) -> dict:
    r=close.pct_change(); var=r.pow(2)
    v=asof_strict(close.index,vix)
    var1=var.shift(1); rvw=var.shift(1).rolling(5).mean(); rvm=var.shift(1).rolling(22).mean()
    X0=pd.DataFrame({"rv1":var1,"rvw":rvw,"rvm":rvm},index=close.index)
    vchg=v.pct_change()
    vz=(v-v.shift(1).rolling(60).mean())/v.shift(1).rolling(60).std(ddof=0)
    X1=X0.copy(); X1["vix_level_z"]=vz; X1["vix_change"]=vchg
    start=int(request["oos_start_days"])
    p0=ols_predict_expanding(X0,var,start,positive=True)
    p1=ols_predict_expanding(X1,var,start,positive=True)
    df=pd.DataFrame({"actual":var,"base":p0,"vix":p1}).dropna()
    q0=qlike(df.actual,df.base); q1=qlike(df.actual,df.vix)
    m0=mse(df.actual,df.base); m1=mse(df.actual,df.vix)
    boot=request["bootstrap"]
    return {
      "proxy":"VIXCLS",
      "oos_days":len(df),
      "base_qlike":float(q0.mean()),"vix_qlike":float(q1.mean()),
      "base_mse":float(m0.mean()),"vix_mse":float(m1.mean()),
      "qlike_improvement":float((q0-q1).mean()),
      "mse_improvement":float((m0-m1).mean()),
      "qlike_improvement_bootstrap":block_bootstrap_mean_ci(q0-q1,int(boot["block_days"]),int(boot["samples"]),int(boot["seed"])),
      "pass_state":bool(q1.mean()<q0.mean()),
      "warning":"VIX is only a free proxy for US option-implied tail risk; a pass does not validate the exact academic tail-risk measure."
    }


def fx_state_test(close: pd.Series, fx: pd.Series, vix: pd.Series, request: dict) -> dict:
    nr=close.pct_change()
    f=asof_strict(close.index,fx)
    v=asof_strict(close.index,vix)
    fxr=f.pct_change()
    median=v.shift(1).expanding(min_periods=100).median()
    high=v>median
    cfg=request["usdjpy_state"]
    boot=request["bootstrap"]
    out={}
    for lag in cfg["lags_days"]:
        x=fxr.rolling(int(lag)).sum()
        rows=pd.DataFrame({"x":x,"y":nr,"high":high}).dropna()
        regimes={}
        for name,mask in [("high_vix",rows.high),("low_vix",~rows.high)]:
            d=rows.loc[mask]
            if len(d)<int(cfg["minimum_regime_observations"]):
                regimes[name]={"n":len(d),"eligible":False}
                continue
            prod=d.x*d.y
            cov=float(np.cov(d.x,d.y,ddof=0)[0,1])
            corr=float(d.x.corr(d.y))
            slope=float(cov/np.var(d.x,ddof=0)) if np.var(d.x,ddof=0)>0 else 0.0
            regimes[name]={
              "n":len(d),"eligible":True,"corr":corr,"slope":slope,
              "association_bootstrap":block_bootstrap_mean_ci(prod,int(boot["block_days"]),int(boot["samples"]),int(boot["seed"]))
            }
        out[str(lag)] = regimes
    return {
      "lags_days":cfg["lags_days"],
      "regime_split":"expanding VIX median using only prior observations",
      "results":out,
      "interpretation_rule":"Use as conditional state only if sign/magnitude differ materially by regime and remain stable in forward OOS; never hard-code a universal sign."
    }


def report_md(result: dict)->str:
    v=result["volatility_state"]; t=result["us_tail_risk_proxy"]; f=result["usdjpy_state"]
    lines=[
      f"# JNU Evidence-State Validation: {result['request_id']}",
      "",
      "## 1. Volatility state",
      f"- Best model: **{v['best_model']}**",
      f"- OOS days: {v['oos_days']}",
      f"- QLIKE improvement vs 20d baseline: {v['qlike_improvement_vs_baseline']:.6g}",
      f"- MSE improvement vs 20d baseline: {v['mse_improvement_vs_baseline']:.6g}",
      f"- State gate: **{'PASS' if v['pass_state'] else 'FAIL'}**",
      "",
      "## 2. US tail-risk proxy",
      f"- Proxy: VIXCLS",
      f"- OOS days: {t['oos_days']}",
      f"- Incremental QLIKE improvement: {t['qlike_improvement']:.6g}",
      f"- Incremental MSE improvement: {t['mse_improvement']:.6g}",
      f"- State gate: **{'PASS' if t['pass_state'] else 'FAIL'}**",
      "- Important: VIX is not the same measure as the academic nonparametric tail-risk variable.",
      "",
      "## 3. USDJPY conditional state",
    ]
    for lag,regs in f["results"].items():
        for regime,vals in regs.items():
            if vals.get("eligible"):
                lines.append(f"- {lag}d / {regime}: n={vals['n']}, corr={vals['corr']:.3f}, slope={vals['slope']:.3f}")
    lines += [
      "",
      "## Rule",
      "- These tests evaluate information-state value, not a trading strategy.",
      "- Passing states may enter the next EV test with rules frozen.",
      "- Failed states are not re-tuned on this sample.",
      ""
    ]
    return "\n".join(lines)


def process(path:Path):
    rid=path.stem
    oj=RESULTS/f"{rid}.json"; om=REPORTS/f"{rid}.md"
    if oj.exists(): return
    req=json.loads(path.read_text(encoding="utf-8"))
    close,vix,fx=load(req)
    result={
      "request_id":rid,"status":"complete",
      "volatility_state":volatility_test(close,req),
      "us_tail_risk_proxy":tail_risk_proxy_test(close,vix,req),
      "usdjpy_state":fx_state_test(close,fx,vix,req),
      "promotion_status":"STATE_INFORMATION_SCREEN_ONLY",
      "generated_at_utc":datetime.now(timezone.utc).isoformat()
    }
    RESULTS.mkdir(exist_ok=True); REPORTS.mkdir(exist_ok=True)
    oj.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    om.write_text(report_md(result),encoding="utf-8")


def main():
    failures=[]
    for p in sorted(REQUESTS.glob("*.json")):
        try: process(p)
        except Exception as e:
            failures.append((p.name,str(e))); traceback.print_exc()
    if failures:
        print(json.dumps({"failures":failures},ensure_ascii=False)); return 1
    return 0

if __name__=="__main__":
    raise SystemExit(main())
