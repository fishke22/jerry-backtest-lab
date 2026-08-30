from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
import time
import traceback
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REQUESTS = ROOT / "volatility_requests"
RESULTS = ROOT / "volatility_results"
REPORTS = ROOT / "volatility_reports"
CACHE = ROOT / ".cache" / "market-data"
DERIVED = ROOT / "cloud_data" / "derived"
MANIFESTS = ROOT / "cloud_data" / "manifests"

UPSTREAM_REPO = "FutureSharks/financial-data"
UPSTREAM_COMMIT = "7ba1d404aa8b0e1c0f71321acebadcbfb9bcca8d"
FILE_BLOBS = {
    2011:"e62e4972f44b407a42ac297aa8beba371e9b32d3",
    2012:"9b50dfb2f8ff8506e0f4f906268e27e67cc0aa12",
    2013:"f1c9f34c04a6dca149a8352c9cc593816ad07d56",
    2014:"a0dc8404dada354e28c930b439261d56213d00fe",
    2015:"787f22e8f151922a8a8b3e3e15032961a86c00e1",
    2016:"264688c4ba87c7cd76d1085324c99783db7aae29",
    2017:"dd2c091c3e265e6a796d5e987049c8802d3e20aa",
    2018:"0ea58be2dfa7910973fbed52831739edc3c07a60",
}
BASE_PATH = "pyfinancialdata/data/stocks/histdata/JPXJPY"
EST_FIXED = timezone(timedelta(hours=-5))

def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def raw_url(year: int) -> str:
    fname = f"DAT_ASCII_JPXJPY_M1_{year}.csv"
    return (
        f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}/"
        f"{BASE_PATH}/{fname}"
    )

def fetch_cached(year: int, force: bool=False) -> tuple[bytes, bool, str]:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"jpxjpy_m1_{year}_{UPSTREAM_COMMIT[:12]}.csv"
    url = raw_url(year)
    if path.exists() and not force:
        return path.read_bytes(), True, url
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent":"Mozilla/5.0 JerryBacktestLab/VolProxy-0.1",
                    "Accept":"text/plain,text/csv,*/*;q=0.8",
                },
            )
            with urllib.request.urlopen(req, timeout=180) as r:
                raw = r.read()
            path.write_bytes(raw)
            return raw, False, url
        except Exception as exc:
            last = exc
            if attempt < 3:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"fetch failed for {year}: {last}")

def parse_year_to_daily_rv(raw: bytes, year: int) -> pd.DataFrame:
    names = ["stamp","open","high","low","close","volume"]
    df = pd.read_csv(
        io.BytesIO(raw),
        sep=";",
        header=None,
        names=names,
        usecols=range(6),
        dtype={"stamp":"string"},
    )
    naive = pd.to_datetime(df["stamp"], format="%Y%m%d %H%M%S", errors="coerce")
    valid = naive.notna()
    df = df.loc[valid].copy()
    naive = naive.loc[valid]
    idx = pd.DatetimeIndex(naive).tz_localize(EST_FIXED).tz_convert("Asia/Tokyo")
    df.index = idx
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["close"]).sort_index()
    df = df[(df.index.year >= year-1) & (df.index.year <= year+1)]

    # Historical TSE cash-session schedule is a data-integrity input, not a model parameter.
    # Before 2011-11-21 the morning cash session ended at 11:00; from 2011-11-21 it ended at 11:30.
    mins = df.index.hour * 60 + df.index.minute
    local_dates = pd.DatetimeIndex(df.index.tz_localize(None)).normalize()
    extension_date = pd.Timestamp("2011-11-21")
    am_end = np.where(local_dates < extension_date, 11*60, 11*60+30)
    am = (mins >= 9*60) & (mins < am_end)
    pm = (mins >= 12*60+30) & (mins < 15*60)
    df = df.loc[am | pm, ["close"]].copy()
    if df.empty:
        raise RuntimeError(f"no Japan cash-session rows after timezone conversion for {year}")

    mins = df.index.hour * 60 + df.index.minute
    df["part"] = np.where(mins < 12*60, "AM", "PM")
    df["trade_date"] = pd.Index(df.index.date)

    rows = []
    for (date, part), g in df.groupby(["trade_date","part"], sort=True):
        g = g.sort_index()
        # 5-minute sampling is fixed by preregistration. Last observed quote in each bin.
        sampled = g["close"].resample("5min").last().dropna()
        if len(sampled) < 5:
            continue
        r = np.log(sampled).diff().dropna()
        if r.empty:
            continue
        rows.append(pd.DataFrame({
            "trade_date":[pd.Timestamp(date)],
            "part":[part],
            "rv":[float(np.sum(np.square(r.to_numpy())))],
            "rsv_pos":[float(np.sum(np.square(r[r>0].to_numpy())))],
            "rsv_neg":[float(np.sum(np.square(r[r<0].to_numpy())))],
            "n_5m_returns":[int(len(r))],
            "last_close":[float(sampled.iloc[-1])],
        }))
    if not rows:
        raise RuntimeError(f"no realized-volatility rows for {year}")
    part_df = pd.concat(rows, ignore_index=True)

    agg = part_df.groupby("trade_date").agg(
        rv=("rv","sum"),
        rsv_pos=("rsv_pos","sum"),
        rsv_neg=("rsv_neg","sum"),
        n_5m_returns=("n_5m_returns","sum"),
        session_parts=("part","nunique"),
    )
    closes = part_df.sort_values(["trade_date","part"]).groupby("trade_date")["last_close"].last()
    agg["session_close"] = closes
    agg["daily_log_return"] = np.log(agg["session_close"]).diff()
    agg["source_year"] = year
    return agg

def build_panel(req: dict) -> tuple[pd.DataFrame, dict]:
    force = bool(req.get("force_refresh", False))
    pieces = []
    sources = {}
    for year in req["years"]:
        year = int(year)
        raw, hit, url = fetch_cached(year, force)
        pieces.append(parse_year_to_daily_rv(raw, year))
        sources[str(year)] = {
            "upstream_repo":UPSTREAM_REPO,
            "upstream_commit":UPSTREAM_COMMIT,
            "upstream_git_blob_sha":FILE_BLOBS[year],
            "url":url,
            "sha256":sha256(raw),
            "cache_hit":bool(hit),
            "raw_storage":"UPSTREAM_PINNED_GITHUB + ACTIONS_CACHE",
        }

    panel = pd.concat(pieces).sort_index()
    # Year files can include adjacent-date spillover after timezone conversion.
    panel = panel[~panel.index.duplicated(keep="last")]
    panel = panel.loc[pd.Timestamp(f"{min(req['years'])}-01-01"):pd.Timestamp(f"{max(req['years'])}-12-31")]
    # Require both AM and PM to avoid partial-day RV distortion.
    panel = panel[panel["session_parts"] == 2].copy()
    panel["daily_log_return"] = np.log(panel["session_close"]).diff()
    return panel, sources

def add_features(panel: pd.DataFrame) -> pd.DataFrame:
    eps = 1e-12
    d = panel.copy()
    d["log_rv"] = np.log(d["rv"].clip(lower=eps))
    d["log_rsv_pos"] = np.log(d["rsv_pos"].clip(lower=eps))
    d["log_rsv_neg"] = np.log(d["rsv_neg"].clip(lower=eps))
    d["lag_logrv_d"] = d["log_rv"].shift(1)
    d["lag_logrv_w"] = d["log_rv"].shift(1).rolling(5).mean()
    d["lag_logrv_m"] = d["log_rv"].shift(1).rolling(22).mean()
    d["lag_neg_daily_return_abs"] = (-d["daily_log_return"].shift(1)).clip(lower=0.0)
    d["lag_log_rsv_pos"] = d["log_rsv_pos"].shift(1)
    d["lag_log_rsv_neg"] = d["log_rsv_neg"].shift(1)
    return d

MODEL_COLS = {
    "HAR_RV":["lag_logrv_d","lag_logrv_w","lag_logrv_m"],
    "HAR_LEVERAGE":["lag_logrv_d","lag_logrv_w","lag_logrv_m","lag_neg_daily_return_abs"],
    "HAR_RSV":["lag_log_rsv_pos","lag_log_rsv_neg","lag_logrv_w","lag_logrv_m"],
}

def expanding_forecasts(d: pd.DataFrame, min_train: int) -> pd.DataFrame:
    out = pd.DataFrame(index=d.index)
    out["actual_rv"] = d["rv"]
    for model, cols in MODEL_COLS.items():
        pred = pd.Series(np.nan, index=d.index, dtype=float)
        for i in range(min_train, len(d)):
            train = d.iloc[:i][cols + ["log_rv"]].dropna()
            row = d.iloc[i][cols]
            if len(train) < min_train or row.isna().any():
                continue
            X = np.column_stack([np.ones(len(train)), train[cols].to_numpy(float)])
            y = train["log_rv"].to_numpy(float)
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            log_pred = float(np.r_[1.0, row.to_numpy(float)] @ beta)
            pred.iloc[i] = max(float(np.exp(log_pred)), 1e-12)
        out[model] = pred
    return out.dropna()

def qlike(actual: pd.Series, pred: pd.Series) -> pd.Series:
    a,p = actual.align(pred, join="inner")
    a = a.clip(lower=1e-12)
    p = p.clip(lower=1e-12)
    return a/p + np.log(p)

def mse(actual: pd.Series, pred: pd.Series) -> pd.Series:
    a,p = actual.align(pred, join="inner")
    return (a-p)**2

def block_bootstrap(values: pd.Series, block: int, samples: int, seed: int) -> dict:
    x = values.dropna().to_numpy(float)
    n = len(x)
    if n < 30:
        return {"n":n,"mean":float(np.mean(x)) if n else 0.0,"ci95":[0.0,0.0],"prob_positive":0.0}
    block = max(1,min(block,n))
    rng = np.random.default_rng(seed)
    starts = np.arange(0,n-block+1)
    means = np.empty(samples)
    for i in range(samples):
        acc=[]
        while len(acc)<n:
            s=int(rng.choice(starts))
            acc.extend(x[s:s+block])
        means[i]=float(np.mean(acc[:n]))
    lo,hi=np.quantile(means,[0.025,0.975])
    return {
        "n":n,
        "mean":float(np.mean(x)),
        "ci95":[float(lo),float(hi)],
        "prob_positive":float(np.mean(means>0)),
    }

def evaluate(fc: pd.DataFrame, req: dict) -> dict:
    actual=fc["actual_rv"]
    losses={}
    qbase=qlike(actual,fc["HAR_RV"])
    mbase=mse(actual,fc["HAR_RV"])
    for model in MODEL_COLS:
        q=qlike(actual,fc[model])
        m=mse(actual,fc[model])
        losses[model]={
            "qlike":float(q.mean()),
            "mse":float(m.mean()),
        }

    cfg=req["bootstrap"]
    comparisons={}
    for model in ["HAR_LEVERAGE","HAR_RSV"]:
        q=qlike(actual,fc[model])
        m=mse(actual,fc[model])
        qdiff=qbase-q
        mdiff=mbase-m
        sub={}
        for label,start,end in [
            ("2011_2014","2011-01-01","2014-12-31"),
            ("2015_2018","2015-01-01","2018-12-31"),
        ]:
            mask=(fc.index>=pd.Timestamp(start))&(fc.index<=pd.Timestamp(end))
            sq=qdiff.loc[mask]
            sm=mdiff.loc[mask]
            sub[label]={
                "n":int(mask.sum()),
                "qlike_improvement":float(sq.mean()) if len(sq) else None,
                "mse_improvement":float(sm.mean()) if len(sm) else None,
            }
        qb=block_bootstrap(qdiff,int(cfg["block_days"]),int(cfg["samples"]),int(cfg["seed"]))
        mb=block_bootstrap(mdiff,int(cfg["block_days"]),int(cfg["samples"]),int(cfg["seed"]))
        recent=sub["2015_2018"]
        pass_proxy=(
            losses[model]["qlike"] < losses["HAR_RV"]["qlike"]
            and losses[model]["mse"] < losses["HAR_RV"]["mse"]
            and (recent["qlike_improvement"] is not None and recent["qlike_improvement"] >= 0)
            and (recent["mse_improvement"] is not None and recent["mse_improvement"] >= 0)
            and max(qb["prob_positive"],mb["prob_positive"]) >= float(req["pass_rules"]["min_bootstrap_prob_positive"])
        )
        comparisons[model]={
            "qlike_improvement":float(qdiff.mean()),
            "mse_improvement":float(mdiff.mean()),
            "qlike_bootstrap":qb,
            "mse_bootstrap":mb,
            "subperiods":sub,
            "pass_method_proxy":bool(pass_proxy),
        }
    return {
        "oos_days":int(len(fc)),
        "oos_from":str(fc.index.min().date()),
        "oos_to":str(fc.index.max().date()),
        "losses":losses,
        "comparisons":comparisons,
        "best_by_qlike":min(losses,key=lambda x:losses[x]["qlike"]),
        "best_by_mse":min(losses,key=lambda x:losses[x]["mse"]),
        "any_method_proxy_pass":any(x["pass_method_proxy"] for x in comparisons.values()),
    }

def report(result: dict) -> str:
    e=result["evaluation"]
    lines=[
        f"# JNU Intraday Volatility Method Proxy — {result['request_id']}",
        "",
        f"- Status: **{result['promotion_status']}**",
        f"- OOS days: {e['oos_days']} ({e['oos_from']} → {e['oos_to']})",
        f"- Best QLIKE: **{e['best_by_qlike']}**",
        f"- Best MSE: **{e['best_by_mse']}**",
        f"- Any proxy-method pass: **{e['any_method_proxy_pass']}**",
        "",
        "## Losses",
    ]
    for model,m in e["losses"].items():
        lines.append(f"- {model}: QLIKE={m['qlike']:.8g}, MSE={m['mse']:.8g}")
    lines += ["","## Incremental tests vs HAR_RV"]
    for model,c in e["comparisons"].items():
        lines.append(
            f"- {model}: QLIKE Δ={c['qlike_improvement']:.8g}, "
            f"MSE Δ={c['mse_improvement']:.8g}, "
            f"Pboot(QLIKE>0)={c['qlike_bootstrap']['prob_positive']:.3f}, "
            f"Pboot(MSE>0)={c['mse_bootstrap']['prob_positive']:.3f}, "
            f"PASS={c['pass_method_proxy']}"
        )
        for label,s in c["subperiods"].items():
            lines.append(
                f"  - {label}: n={s['n']}, QLIKE Δ={s['qlike_improvement']}, MSE Δ={s['mse_improvement']}"
            )
    lines += [
        "",
        "## Guardrail",
        "- This is a Nikkei index-proxy methodology test, not OSE/JNU validation.",
        "- Session, 5-minute sampling, HAR windows and model family were preregistered before results.",
        "- No failed model may be rescued by changing windows on this sample.",
        "- Formal JNU use requires the same frozen method on approved OSE/JNU intraday data.",
        "",
    ]
    return "\n".join(lines)

def process(path: Path) -> None:
    req=json.loads(path.read_text(encoding="utf-8"))
    rid=path.stem
    if req.get("request_id")!=rid:
        raise ValueError("request_id must match filename")
    RESULTS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    DERIVED.mkdir(parents=True,exist_ok=True)
    MANIFESTS.mkdir(parents=True,exist_ok=True)
    oj=RESULTS/f"{rid}.json"
    om=REPORTS/f"{rid}.md"
    dp=DERIVED/f"{rid}_rv_panel.csv.gz"
    mp=MANIFESTS/f"{rid}_rv_panel.json"
    if oj.exists():
        print(f"skip {rid}: result exists")
        return

    panel,sources=build_panel(req)
    d=add_features(panel)
    fc=expanding_forecasts(d,int(req["minimum_training_days"]))
    ev=evaluate(fc,req)

    # Durable derived panel: no raw minute bars are copied into the private repo.
    durable_cols=[
        "rv","rsv_pos","rsv_neg","n_5m_returns","session_parts","daily_log_return",
        "log_rv","log_rsv_pos","log_rsv_neg"
    ]
    derived=d[durable_cols].copy()
    compressed=gzip.compress(derived.to_csv(index=True).encode("utf-8"),compresslevel=9)
    dp.write_bytes(compressed)
    derived_sha=sha256(compressed)

    manifest={
        "dataset_id":"NIKKEI_INDEX_PROXY_INTRADAY_RV_2011_2018_V1",
        "status":"DURABLE_DERIVED_PROXY_DATASET",
        "source_identity":{
            "repo":UPSTREAM_REPO,
            "commit":UPSTREAM_COMMIT,
            "instrument":"JPXJPY index proxy, not OSE futures",
            "native_timestamp":"fixed EST UTC-5 without DST",
        },
        "sources":sources,
        "transform":{
            "timezone":"fixed EST UTC-5 to Asia/Tokyo",
            "sessions":["09:00-11:30 JST","12:30-15:00 JST"],
            "sampling":"5-minute last quote inside AM/PM separately",
            "rv":"sum squared 5-minute log returns",
            "no_lunch_gap_return":True,
        },
        "rows":int(len(derived)),
        "path":str(dp.relative_to(ROOT)).replace("\\","/"),
        "sha256":derived_sha,
        "raw_storage_policy":"Raw minute files remain at pinned public upstream plus GitHub Actions cache; private repo stores derived RV panel and provenance.",
        "formal_validation":"PROHIBITED_WITH_THIS_PROXY",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
    }
    mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    result={
        "request_id":rid,
        "candidate_id":"INTRADAY_VOLATILITY_METHOD_PROXY",
        "status":"complete",
        "promotion_status":"METHOD_PROXY_ONLY",
        "preregistration":req["preregistration"],
        "source_manifest":str(mp.relative_to(ROOT)).replace("\\","/"),
        "derived_dataset":str(dp.relative_to(ROOT)).replace("\\","/"),
        "derived_dataset_sha256":derived_sha,
        "panel_days":int(len(panel)),
        "evaluation":ev,
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
    }
    oj.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    om.write_text(report(result),encoding="utf-8")
    print(f"completed {rid}")

def main() -> int:
    REQUESTS.mkdir(exist_ok=True)
    failures=[]
    for p in sorted(REQUESTS.glob("*.json")):
        try:
            process(p)
        except Exception as exc:
            failures.append((p.name,str(exc)))
            traceback.print_exc()
    if failures:
        print(json.dumps({"failures":failures},ensure_ascii=False))
        return 1
    return 0

if __name__=="__main__":
    raise SystemExit(main())
