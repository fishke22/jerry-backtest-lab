from __future__ import annotations

import io
import json
import math
import time
import traceback
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REQUESTS = ROOT / "phase4b_requests"
RESULTS = ROOT / "phase4b_results"
REPORTS = ROOT / "phase4b_reports"
CACHE = ROOT / ".cache" / "market-data"

FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={start}&coed={end}"
CBOE_VIX = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"
GDELT_DOC = "https://api.gdeltproject.org/api/v2/doc/doc"


def fetch(url: str, cache_name: str, force: bool=False, timeout: int=120) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / cache_name
    if path.exists() and not force:
        return path.read_bytes()
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 JerryBacktestLab/0.5",
                    "Accept": "application/json,text/csv,*/*;q=0.8",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            path.write_bytes(raw)
            return raw
        except Exception as exc:
            last = exc
            if attempt < 3:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"fetch failed {cache_name}: {last}")


def parse_nikkei(raw: bytes) -> pd.Series:
    df = pd.read_csv(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
    idx = pd.to_datetime(df.iloc[:, 0], errors="coerce")
    val = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    s = pd.Series(val.to_numpy(), index=idx, name="nikkei").dropna().sort_index()
    return s[~s.index.duplicated(keep="last")]


def parse_fred(raw: bytes, series: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
    date_col = "DATE" if "DATE" in df.columns else (
        "observation_date" if "observation_date" in df.columns else df.columns[0]
    )
    value_col = series if series in df.columns else df.columns[-1]
    idx = pd.to_datetime(df[date_col], errors="coerce")
    val = pd.to_numeric(df[value_col], errors="coerce")
    s = pd.Series(val.to_numpy(), index=idx, name=series).dropna().sort_index()
    return s[~s.index.duplicated(keep="last")]


def parse_cboe_vix(raw: bytes) -> pd.Series:
    df = pd.read_csv(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
    cols = {str(x).strip().upper(): x for x in df.columns}
    date_col = cols.get("DATE", df.columns[0])
    close_col = cols.get("CLOSE", df.columns[-1])
    idx = pd.to_datetime(df[date_col], errors="coerce")
    val = pd.to_numeric(df[close_col], errors="coerce")
    s = pd.Series(val.to_numpy(), index=idx, name="VIX").dropna().sort_index()
    return s[~s.index.duplicated(keep="last")]


def asof_strict(target_index: pd.DatetimeIndex, source: pd.Series) -> pd.Series:
    left = pd.DataFrame({"target": target_index}).sort_values("target")
    right = source.rename("value").reset_index()
    right.columns = ["source_date", "value"]
    right = right.sort_values("source_date")
    merged = pd.merge_asof(
        left,
        right,
        left_on="target",
        right_on="source_date",
        direction="backward",
        allow_exact_matches=False,
    )
    return pd.Series(merged["value"].to_numpy(), index=target_index, name=source.name)


def expanding_ols_predict(X: pd.DataFrame, y: pd.Series, start: int) -> pd.Series:
    pred = pd.Series(np.nan, index=y.index, dtype=float)
    for i in range(start, len(y)):
        train = pd.concat([X.iloc[:i], y.iloc[:i].rename("y")], axis=1).dropna()
        row = X.iloc[i]
        if len(train) < max(80, X.shape[1] * 12) or row.isna().any():
            continue
        A = np.column_stack([np.ones(len(train)), train[X.columns].to_numpy(dtype=float)])
        b = train["y"].to_numpy(dtype=float)
        beta, *_ = np.linalg.lstsq(A, b, rcond=None)
        pred.iloc[i] = float(np.r_[1.0, row.to_numpy(dtype=float)] @ beta)
    return pred


def block_bootstrap_mean(values: pd.Series, block: int, samples: int, seed: int) -> dict:
    x = values.dropna().to_numpy(dtype=float)
    n = len(x)
    if n < 30:
        return {"mean": float(np.mean(x)) if n else 0.0, "ci95": [0.0, 0.0], "prob_positive": 0.0}
    block = max(1, min(block, n))
    rng = np.random.default_rng(seed)
    starts = np.arange(0, n - block + 1)
    means = np.empty(samples, dtype=float)
    for i in range(samples):
        out = []
        while len(out) < n:
            s = int(rng.choice(starts))
            out.extend(x[s:s+block])
        means[i] = float(np.mean(out[:n]))
    lo, hi = np.quantile(means, [0.025, 0.975])
    return {
        "mean": float(np.mean(x)),
        "ci95": [float(lo), float(hi)],
        "prob_positive": float(np.mean(means > 0.0)),
    }


def holm_from_tail_probs(tail_p: dict[str, float], alpha: float) -> dict:
    ordered = sorted(tail_p.items(), key=lambda kv: kv[1])
    m = len(ordered)
    adjusted = {}
    reject = {k: False for k in tail_p}
    running = 0.0
    stop = False
    for rank, (name, p) in enumerate(ordered, start=1):
        adj = min(1.0, (m-rank+1) * p)
        running = max(running, adj)
        adjusted[name] = running
        threshold = alpha / (m-rank+1)
        if not stop and p <= threshold:
            reject[name] = True
        else:
            stop = True
    return {"alpha": alpha, "raw_tail_p": tail_p, "adjusted_p": adjusted, "reject": reject}


def qlike(actual_var: pd.Series, pred_var: pd.Series) -> pd.Series:
    a, p = actual_var.align(pred_var, join="inner")
    a = a.clip(lower=1e-12)
    p = p.clip(lower=1e-12)
    return a / p + np.log(p)


def parse_gdelt_points(obj) -> list[tuple[pd.Timestamp, float]]:
    points = []
    def walk(x):
        if isinstance(x, dict):
            lower = {str(k).lower(): k for k in x}
            if "date" in lower and "value" in lower:
                dt = pd.to_datetime(x[lower["date"]], errors="coerce", utc=True)
                try:
                    val = float(x[lower["value"]])
                except Exception:
                    val = np.nan
                if pd.notna(dt) and np.isfinite(val):
                    points.append((dt.tz_convert(None).normalize(), val))
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(obj)
    return points


def gdelt_timeline(query: str, mode: str, start: str, end: str, cache_name: str, force: bool) -> pd.Series:
    params = {
        "query": query,
        "mode": mode,
        "format": "json",
        "startdatetime": start,
        "enddatetime": end,
    }
    url = GDELT_DOC + "?" + urllib.parse.urlencode(params)
    raw = fetch(url, cache_name, force, timeout=180)
    try:
        obj = json.loads(raw.decode("utf-8-sig", errors="replace"))
    except Exception as exc:
        raise RuntimeError(f"GDELT returned non-JSON for {cache_name}: {exc}")
    pts = parse_gdelt_points(obj)
    if not pts:
        raise RuntimeError(f"No GDELT timeline points parsed for {cache_name}")
    df = pd.DataFrame(pts, columns=["date", "value"])
    s = df.groupby("date")["value"].mean().sort_index()
    s.name = mode
    return s


def load_market(req: dict):
    suite = json.loads((ROOT / req["source_suite_result"]).read_text(encoding="utf-8"))
    src = suite["data"]["sources"]
    nk = parse_nikkei(fetch(src["nikkei_futures"]["url"], "nikkei_futures_daily.csv", bool(req.get("force_refresh"))))
    nk = nk.loc[req["date_from"]:req["date_to"]]
    start = (pd.Timestamp(req["date_from"]) - pd.Timedelta(days=500)).date().isoformat()
    end = pd.Timestamp(req["date_to"]).date().isoformat()
    fx = parse_fred(
        fetch(FRED.format(series="DEXJPUS", start=start, end=end), "fred_dexjpus.csv", bool(req.get("force_refresh"))),
        "DEXJPUS",
    )
    vix = parse_cboe_vix(fetch(CBOE_VIX, "cboe_vix_history.csv", bool(req.get("force_refresh"))))
    return nk, fx, vix.loc[pd.Timestamp(start):pd.Timestamp(end)]


def test_usdjpy(close: pd.Series, fx: pd.Series, vix: pd.Series, req: dict) -> dict:
    r = close.pct_change()
    fx_asof = asof_strict(close.index, fx)
    fx1 = fx_asof.pct_change()
    vix_asof = asof_strict(close.index, vix)

    X0 = pd.DataFrame(index=close.index)
    X0["r1"] = r.shift(1)
    X0["r5"] = r.shift(1).rolling(5).sum()
    X0["rv20"] = r.shift(1).rolling(20).std(ddof=0)
    X1 = X0.copy()
    X1["fx1"] = fx1

    start = int(req["oos_start_days"])
    p0 = expanding_ols_predict(X0, r, start)
    p1 = expanding_ols_predict(X1, r, start)
    df = pd.DataFrame({"y": r, "base": p0, "fx": p1, "vix": vix_asof}).dropna()

    loss0 = (df.y - df.base) ** 2
    loss1 = (df.y - df.fx) ** 2
    diff = loss0 - loss1

    sign0 = (np.sign(df.base) == np.sign(df.y)).astype(float)
    sign1 = (np.sign(df.fx) == np.sign(df.y)).astype(float)

    prior_med = df.vix.shift(1).expanding(min_periods=100).median()
    high = df.vix > prior_med

    cfg = req["usdjpy"]
    boot = req["bootstrap"]
    b = block_bootstrap_mean(diff, int(boot["block_days"]), int(boot["samples"]), int(boot["seed"]))
    regimes = {}
    for name, mask in [("high_vix", high), ("low_vix", ~high)]:
        d = diff.loc[mask.fillna(False)]
        regimes[name] = {
            "n": int(len(d)),
            "mse_improvement": float(d.mean()) if len(d) else 0.0,
            "bootstrap": block_bootstrap_mean(d, int(boot["block_days"]), int(boot["samples"]), int(boot["seed"])),
        }

    pass_state = (
        float(loss1.mean()) < float(loss0.mean())
        and b["prob_positive"] >= float(cfg["min_bootstrap_mse_improvement_probability"])
        and (float(sign1.mean()) >= float(sign0.mean()) if cfg.get("require_sign_accuracy_not_worse", True) else True)
    )
    return {
        "oos_days": int(len(df)),
        "baseline_mse": float(loss0.mean()),
        "with_usdjpy_mse": float(loss1.mean()),
        "mse_improvement": float(diff.mean()),
        "bootstrap": b,
        "baseline_sign_accuracy": float(sign0.mean()),
        "with_usdjpy_sign_accuracy": float(sign1.mean()),
        "regimes": regimes,
        "pass_incremental_state": bool(pass_state),
        "trading_status": "NOT_TESTED",
    }


def news_features(query: str, close_index: pd.DatetimeIndex, req: dict, key: str) -> pd.DataFrame:
    start = pd.Timestamp(req["date_from"]).strftime("%Y%m%d000000")
    end = (pd.Timestamp(req["date_to"]) + pd.Timedelta(days=1)).strftime("%Y%m%d000000")
    force = bool(req.get("force_refresh"))
    tone = gdelt_timeline(query, "TimelineTone", start, end, f"gdelt_{key}_tone.json", force)
    vol = gdelt_timeline(query, "TimelineVol", start, end, f"gdelt_{key}_vol.json", force)

    base = pd.DataFrame({"tone": tone, "volume": vol}).sort_index()
    base["abs_tone"] = base["tone"].abs()
    base["tone_ewm"] = base["tone"].ewm(halflife=float(req["news"]["half_life_days"]), adjust=False).mean()

    out = pd.DataFrame(index=close_index)
    for col in base.columns:
        out[col] = asof_strict(close_index, base[col])
    return out


def test_news(close: pd.Series, req: dict) -> dict:
    r = close.pct_change()
    var = r.pow(2)
    eps = 1e-10

    X0 = pd.DataFrame(index=close.index)
    X0["logv1"] = np.log(var.shift(1) + eps)
    X0["logv5"] = np.log(var.shift(1).rolling(5).mean() + eps)
    X0["logv22"] = np.log(var.shift(1).rolling(22).mean() + eps)

    ylog = np.log(var + eps)
    start = int(req["oos_start_days"])
    base_log = expanding_ols_predict(X0, ylog, start)
    base_var = np.exp(base_log)

    categories = req["news"]["categories"]
    boot_cfg = req["bootstrap"]
    recent_days = int(req["recent_days"])
    raw_results = {}
    tail_p = {}

    for key, query in categories.items():
        nf = news_features(query, close.index, req, key)
        X1 = pd.concat([X0, nf], axis=1)
        aug_log = expanding_ols_predict(X1, ylog, start)
        aug_var = np.exp(aug_log)

        df = pd.DataFrame({"actual": var, "base": base_var, "aug": aug_var}).dropna()
        q0 = qlike(df.actual, df.base)
        q1 = qlike(df.actual, df.aug)
        m0 = (df.actual - df.base) ** 2
        m1 = (df.actual - df.aug) ** 2

        qdiff = q0 - q1
        mdiff = m0 - m1
        bq = block_bootstrap_mean(qdiff, int(boot_cfg["block_days"]), int(boot_cfg["samples"]), int(boot_cfg["seed"]))
        bm = block_bootstrap_mean(mdiff, int(boot_cfg["block_days"]), int(boot_cfg["samples"]), int(boot_cfg["seed"]))
        tail_p[key] = max(0.0, 1.0 - bq["prob_positive"])

        recent = df.tail(recent_days)
        rq0 = qlike(recent.actual, recent.base)
        rq1 = qlike(recent.actual, recent.aug)
        rm0 = (recent.actual - recent.base) ** 2
        rm1 = (recent.actual - recent.aug) ** 2

        raw_results[key] = {
            "query": query,
            "oos_days": int(len(df)),
            "qlike_improvement": float(qdiff.mean()),
            "mse_improvement": float(mdiff.mean()),
            "qlike_bootstrap": bq,
            "mse_bootstrap": bm,
            "recent_qlike_improvement": float((rq0-rq1).mean()),
            "recent_mse_improvement": float((rm0-rm1).mean()),
        }

    holm = holm_from_tail_probs(tail_p, float(req["news"]["holm_alpha"]))
    threshold = float(req["news"]["min_bootstrap_qlike_improvement_probability"])

    survivors = []
    for key, row in raw_results.items():
        checks = {
            "qlike_improves": row["qlike_improvement"] > 0,
            "mse_improves": row["mse_improvement"] > 0,
            "bootstrap_qlike": row["qlike_bootstrap"]["prob_positive"] >= threshold,
            "recent_qlike": row["recent_qlike_improvement"] >= 0,
            "recent_mse": row["recent_mse_improvement"] >= 0,
            "holm": bool(holm["reject"][key]),
        }
        row["checks"] = checks
        row["status"] = "NEWS_STATE_CANDIDATE" if all(checks.values()) else "FAIL_NEWS_STATE"
        if row["status"] == "NEWS_STATE_CANDIDATE":
            survivors.append(key)

    return {
        "source": "GDELT DOC 2.0 TimelineTone/TimelineVol",
        "categories": raw_results,
        "multiple_testing": holm,
        "survivors": survivors,
        "directional_trading_status": "NOT_TESTED",
    }


def report_md(result: dict) -> str:
    u = result["usdjpy"]
    n = result["news"]
    lines = [
        f"# JNU Phase4B Evidence: {result['request_id']}",
        "",
        "## USDJPY 1-day incremental state",
        f"- OOS days: {u['oos_days']}",
        f"- MSE improvement: {u['mse_improvement']:.6g}",
        f"- Bootstrap P(improvement > 0): {u['bootstrap']['prob_positive']:.1%}",
        f"- Sign accuracy: {u['baseline_sign_accuracy']:.1%} -> {u['with_usdjpy_sign_accuracy']:.1%}",
        f"- State gate: **{'PASS' if u['pass_incremental_state'] else 'FAIL'}**",
        "",
        "## News / sentiment state",
        "",
        "| Category | QLIKE Δ | MSE Δ | Bootstrap P+ | Recent QLIKE Δ | Holm | Status |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for key,row in n["categories"].items():
        lines.append(
            f"| {key} | {row['qlike_improvement']:.6g} | {row['mse_improvement']:.6g} | "
            f"{row['qlike_bootstrap']['prob_positive']:.1%} | {row['recent_qlike_improvement']:.6g} | "
            f"{'PASS' if row['checks']['holm'] else 'FAIL'} | {row['status']} |"
        )
    lines += [
        "",
        f"- News-state survivors: {', '.join(n['survivors']) if n['survivors'] else 'None'}",
        "",
        "## Interpretation",
        "- This stage tests incremental information, not trading P&L.",
        "- Same-day external information is excluded by strict as-of alignment.",
        "- Failed news categories are not reworded or reweighted to rescue them.",
        "- A NEWS_STATE_CANDIDATE may enter a later EV test with its query/specification frozen.",
        "",
    ]
    return "\n".join(lines)


def process(path: Path):
    rid = path.stem
    outj = RESULTS / f"{rid}.json"
    outm = REPORTS / f"{rid}.md"
    if outj.exists():
        return
    req = json.loads(path.read_text(encoding="utf-8"))
    close, fx, vix = load_market(req)
    result = {
        "request_id": rid,
        "status": "complete",
        "usdjpy": test_usdjpy(close, fx, vix, req),
        "news": test_news(close, req),
        "promotion_status": "INFORMATION_STATE_SCREEN_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    RESULTS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    outj.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    outm.write_text(report_md(result), encoding="utf-8")


def main():
    failures = []
    for p in sorted(REQUESTS.glob("*.json")):
        try:
            process(p)
        except Exception as exc:
            failures.append((p.name, str(exc)))
            traceback.print_exc()
    if failures:
        print(json.dumps({"failures": failures}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
