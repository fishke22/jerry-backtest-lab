from __future__ import annotations

import hashlib
import io
import itertools
import json
import math
import sys
import traceback
import urllib.request
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt

ROOT = Path(__file__).resolve().parents[1]
REQUESTS = ROOT / "suite_requests"
RESULTS = ROOT / "suite_results"
REPORTS = ROOT / "suite_reports"
CACHE = ROOT / ".cache" / "market-data"

NIKKEI_FUTURES_CSV = (
    "https://indexes.nikkei.co.jp/nkave/historical/"
    "nikkei_225_futures_index_series_daily_en.csv"
)
FRED_CSV = (
    "https://fred.stlouisfed.org/graph/fredgraph.csv"
    "?id={series_id}&cosd={start}&coed={end}"
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fetch_cached(url: str, cache_name: str, force_refresh: bool = False) -> tuple[bytes, bool]:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / cache_name
    if path.exists() and not force_refresh:
        return path.read_bytes(), True

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 JerryBacktestLab/0.2",
                    "Accept": "text/csv,*/*;q=0.8",
                },
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                raw = response.read()
            path.write_bytes(raw)
            return raw, False
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch {cache_name} after 3 attempts: {last_error}")


def parse_nikkei(raw: bytes) -> pd.Series:
    text = raw.decode("utf-8-sig", errors="replace")
    df = pd.read_csv(io.StringIO(text))
    if df.shape[1] < 2:
        raise RuntimeError("Unexpected Nikkei Futures Index CSV shape")
    dates = pd.to_datetime(df.iloc[:, 0], errors="coerce")
    values = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    s = pd.Series(values.to_numpy(), index=dates, name="nikkei_futures").dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


def parse_fred(raw: bytes, series_id: str) -> pd.Series:
    text = raw.decode("utf-8-sig", errors="replace")
    df = pd.read_csv(io.StringIO(text))
    if "DATE" in df.columns:
        date_col = "DATE"
    elif "observation_date" in df.columns:
        date_col = "observation_date"
    else:
        date_col = df.columns[0]
    value_col = series_id if series_id in df.columns else df.columns[-1]
    dates = pd.to_datetime(df[date_col], errors="coerce")
    values = pd.to_numeric(df[value_col], errors="coerce")
    s = pd.Series(values.to_numpy(), index=dates, name=series_id).dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


def load_data(request: dict) -> tuple[pd.Series, dict[str, pd.Series], dict]:
    force = bool(request.get("force_refresh", False))
    nk_raw, nk_hit = fetch_cached(NIKKEI_FUTURES_CSV, "nikkei_futures_daily.csv", force)
    date_from = pd.Timestamp(request.get("date_from", "2000-01-01"))
    date_to = pd.Timestamp(request.get("date_to", datetime.now(timezone.utc).date()))
    fred_start = (date_from - pd.Timedelta(days=450)).date().isoformat()
    fred_end = date_to.date().isoformat()
    ndx_url = FRED_CSV.format(series_id="NASDAQ100", start=fred_start, end=fred_end)
    fx_url = FRED_CSV.format(series_id="DEXJPUS", start=fred_start, end=fred_end)
    ndx_raw, ndx_hit = fetch_cached(ndx_url, "fred_nasdaq100.csv", force)
    fx_raw, fx_hit = fetch_cached(fx_url, "fred_dexjpus.csv", force)

    close = parse_nikkei(nk_raw)
    ndx = parse_fred(ndx_raw, "NASDAQ100")
    fx = parse_fred(fx_raw, "DEXJPUS")

    if request.get("date_from"):
        close = close.loc[pd.Timestamp(request["date_from"]):]
    if request.get("date_to"):
        close = close.loc[:pd.Timestamp(request["date_to"])]

    if len(close) < 400:
        raise ValueError("JNU daily proxy suite requires at least 400 Nikkei observations")

    ext = {
        "ndx": ndx.reindex(close.index).ffill(),
        "usdjpy": fx.reindex(close.index).ffill(),
    }

    source_meta = {
        "nikkei_futures": {
            "url": NIKKEI_FUTURES_CSV,
            "sha256": sha256(nk_raw),
            "cache_hit": nk_hit,
            "raw_committed": False,
        },
        "nasdaq100_fred": {
            "url": ndx_url,
            "sha256": sha256(ndx_raw),
            "cache_hit": ndx_hit,
            "raw_committed": False,
            "note": "Used only as an ephemeral/private research input; raw series is not committed.",
        },
        "usdjpy_fred": {
            "url": fx_url,
            "sha256": sha256(fx_raw),
            "cache_hit": fx_hit,
            "raw_committed": False,
        },
    }
    return close, ext, source_meta


def sign_series(x: pd.Series) -> pd.Series:
    return pd.Series(np.sign(x.fillna(0.0)), index=x.index, dtype=float)


def momentum_signal(close: pd.Series, params: dict) -> pd.Series:
    lb = int(params["lookback"])
    return sign_series(close / close.shift(lb) - 1.0)


def breakout_signal(close: pd.Series, params: dict) -> pd.Series:
    lb = int(params["lookback"])
    upper = close.shift(1).rolling(lb).max()
    lower = close.shift(1).rolling(lb).min()
    events = pd.Series(np.nan, index=close.index, dtype=float)
    events.loc[close > upper] = 1.0
    events.loc[close < lower] = -1.0
    return events.ffill().fillna(0.0)


def volatility_regime_signal(close: pd.Series, params: dict) -> pd.Series:
    mom_lb = int(params["momentum_lookback"])
    vol_lb = int(params["vol_lookback"])
    regime = str(params["regime"])
    mom = close / close.shift(mom_lb) - 1.0
    rv = close.pct_change().rolling(vol_lb).std(ddof=0) * math.sqrt(252.0)
    rv_median = rv.rolling(126, min_periods=40).median()
    if regime == "low":
        allowed = rv <= rv_median
    else:
        allowed = rv > rv_median
    return sign_series(mom).where(allowed, 0.0).fillna(0.0)


def drawdown_repair_signal(close: pd.Series, params: dict) -> pd.Series:
    peak_lb = int(params["peak_lookback"])
    threshold = float(params["drawdown_threshold"])
    repair_lb = int(params["repair_lookback"])

    peak = close.rolling(peak_lb, min_periods=max(20, peak_lb // 3)).max()
    dd = close / peak - 1.0
    repair_mom = close / close.shift(repair_lb) - 1.0

    out = pd.Series(0.0, index=close.index, dtype=float)
    armed = False
    active = False
    for i in range(len(close)):
        d = dd.iloc[i]
        m = repair_mom.iloc[i]
        if not np.isfinite(d) or not np.isfinite(m):
            continue
        if d <= -threshold:
            armed = True
        if armed and not active and d > -(threshold * 0.75) and m > 0.0:
            active = True
            armed = False
        if active and (m < 0.0 or d <= -(threshold * 1.25)):
            active = False
        out.iloc[i] = 1.0 if active else 0.0
    return out


def relative_strength_signal(close: pd.Series, ext: dict[str, pd.Series], params: dict) -> pd.Series:
    lb = int(params["lookback"])
    j = close / close.shift(lb) - 1.0
    n = ext["ndx"] / ext["ndx"].shift(lb) - 1.0
    return sign_series(j - n)


def cross_market_signal(close: pd.Series, ext: dict[str, pd.Series], params: dict) -> pd.Series:
    lb = int(params["lookback"])
    mode = str(params["mode"])
    j = sign_series(close / close.shift(lb) - 1.0)
    n = sign_series(ext["ndx"] / ext["ndx"].shift(lb) - 1.0)
    f = sign_series(ext["usdjpy"] / ext["usdjpy"].shift(lb) - 1.0)

    if mode == "unanimous":
        long = (j > 0) & (n > 0) & (f > 0)
        short = (j < 0) & (n < 0) & (f < 0)
    else:
        votes = j + n + f
        long = votes >= 1.0
        short = votes <= -1.0

    out = pd.Series(0.0, index=close.index, dtype=float)
    out.loc[long] = 1.0
    out.loc[short] = -1.0
    return out


def module_grid(module: str) -> list[dict]:
    if module == "trend_momentum":
        return [{"lookback": x} for x in [10, 20, 60, 120]]
    if module == "breakout":
        return [{"lookback": x} for x in [20, 55, 100]]
    if module == "volatility_regime":
        return [
            {"momentum_lookback": m, "vol_lookback": v, "regime": r}
            for m, v, r in itertools.product([20, 60], [20, 60], ["low", "high"])
        ]
    if module == "drawdown_repair":
        return [
            {
                "peak_lookback": p,
                "drawdown_threshold": d,
                "repair_lookback": r,
            }
            for p, d, r in itertools.product([60, 120], [0.05, 0.10, 0.15], [3, 5, 10])
        ]
    if module == "relative_strength_ndx":
        return [{"lookback": x} for x in [20, 60, 120]]
    if module == "cross_market_confirmation":
        return [
            {"lookback": x, "mode": mode}
            for x, mode in itertools.product([10, 20, 60], ["majority", "unanimous"])
        ]
    raise ValueError(f"Unknown module: {module}")


def module_signal(module: str, close: pd.Series, ext: dict[str, pd.Series], params: dict) -> pd.Series:
    if module == "trend_momentum":
        return momentum_signal(close, params)
    if module == "breakout":
        return breakout_signal(close, params)
    if module == "volatility_regime":
        return volatility_regime_signal(close, params)
    if module == "drawdown_repair":
        return drawdown_repair_signal(close, params)
    if module == "relative_strength_ndx":
        return relative_strength_signal(close, ext, params)
    if module == "cross_market_confirmation":
        return cross_market_signal(close, ext, params)
    raise ValueError(module)


def returns_from_signal(
    close: pd.Series,
    signal: pd.Series,
    cost_bps: float,
    slippage_bps: float,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    position = signal.shift(1).fillna(0.0).clip(-1.0, 1.0)
    market_ret = close.pct_change().fillna(0.0)
    gross = position * market_ret
    turnover = position.diff().abs()
    if len(turnover):
        turnover.iloc[0] = abs(position.iloc[0])
    one_way_cost = (cost_bps + slippage_bps) / 10_000.0
    net = gross - turnover * one_way_cost
    return net.astype(float), gross.astype(float), turnover.astype(float)


def metrics(r: pd.Series, turnover: pd.Series | None = None) -> dict:
    r = r.dropna().astype(float)
    if len(r) == 0:
        return {
            "days": 0,
            "total_return": 0.0,
            "annualized_return": 0.0,
            "annualized_volatility": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "hit_rate": 0.0,
            "turnover": 0.0,
        }
    equity = (1.0 + r).cumprod()
    total_return = float(equity.iloc[-1] - 1.0)
    years = len(r) / 252.0
    ann_ret = (
        float(equity.iloc[-1] ** (1.0 / years) - 1.0)
        if years > 0 and equity.iloc[-1] > 0
        else -1.0
    )
    std = float(r.std(ddof=0))
    ann_vol = std * math.sqrt(252.0)
    sharpe = float(r.mean() / std * math.sqrt(252.0)) if std > 0 else 0.0
    dd = equity / equity.cummax() - 1.0
    nonzero = r[r != 0.0]
    return {
        "days": int(len(r)),
        "total_return": total_return,
        "annualized_return": ann_ret,
        "annualized_volatility": ann_vol,
        "sharpe": sharpe,
        "max_drawdown": float(dd.min()),
        "hit_rate": float((nonzero > 0).mean()) if len(nonzero) else 0.0,
        "turnover": float(turnover.loc[r.index].sum()) if turnover is not None else 0.0,
    }


def score(metric_name: str, m: dict) -> float:
    if metric_name == "total_return":
        return float(m["total_return"])
    if metric_name == "annualized_return":
        return float(m["annualized_return"])
    return float(m["sharpe"])


def bootstrap_summary(r: pd.Series, block_days: int, samples: int, seed: int) -> dict:
    values = r.dropna().astype(float).to_numpy()
    n = len(values)
    if n < 20:
        return {"prob_mean_daily_return_positive": 0.0, "mean_daily_return_ci_95": [0.0, 0.0]}
    block_days = max(1, min(block_days, n))
    samples = max(100, samples)
    rng = np.random.default_rng(seed)
    starts = np.arange(0, n - block_days + 1)
    means = np.empty(samples, dtype=float)
    for i in range(samples):
        sample: list[float] = []
        while len(sample) < n:
            start = int(rng.choice(starts))
            sample.extend(values[start : start + block_days])
        means[i] = float(np.mean(sample[:n]))
    low, high = np.quantile(means, [0.025, 0.975])
    return {
        "block_days": int(block_days),
        "samples": int(samples),
        "prob_mean_daily_return_positive": float(np.mean(means > 0.0)),
        "mean_daily_return_ci_95": [float(low), float(high)],
    }


def regime_analysis(close: pd.Series, oos_ret: pd.Series, min_days: int) -> dict:
    prior_close = close.shift(1)
    ma100 = prior_close.rolling(100, min_periods=60).mean()
    prior_market_ret = close.pct_change().shift(1)
    rv20 = prior_market_ret.rolling(20, min_periods=15).std(ddof=0)
    rv_median = rv20.rolling(126, min_periods=40).median()

    regimes = {
        "bull": prior_close > ma100,
        "bear": prior_close <= ma100,
        "high_vol": rv20 > rv_median,
        "low_vol": rv20 <= rv_median,
    }
    output = {}
    eligible_positive = 0
    eligible_total = 0
    for name, mask in regimes.items():
        idx = oos_ret.index.intersection(mask.index[mask.fillna(False)])
        m = metrics(oos_ret.loc[idx]) if len(idx) else metrics(pd.Series(dtype=float))
        eligible = int(m["days"]) >= min_days
        positive = bool(m["total_return"] > 0.0) if eligible else False
        if eligible:
            eligible_total += 1
            eligible_positive += int(positive)
        output[name] = {"eligible": eligible, "positive": positive, "metrics": m}
    ratio = float(eligible_positive / eligible_total) if eligible_total else 0.0
    return {
        "min_regime_days": int(min_days),
        "eligible_regimes": int(eligible_total),
        "positive_regimes": int(eligible_positive),
        "positive_regime_ratio": ratio,
        "regimes": output,
    }


def evaluate_module(
    module: str,
    close: pd.Series,
    ext: dict[str, pd.Series],
    request: dict,
) -> dict:
    wf = request["walk_forward"]
    train_days = int(wf["train_days"])
    test_days = int(wf["test_days"])
    step_days = int(wf.get("step_days", test_days))
    metric_name = str(wf.get("selection_metric", "sharpe"))
    cost_bps = float(request.get("cost_bps", 0.0))
    slippage_bps = float(request.get("slippage_bps", 0.0))

    cache: list[tuple[dict, pd.Series, pd.Series, pd.Series]] = []
    for params in module_grid(module):
        signal = module_signal(module, close, ext, params)
        net, gross, turnover = returns_from_signal(close, signal, cost_bps, slippage_bps)
        cache.append((params, net, gross, turnover))

    folds = []
    oos_net = []
    oos_gross = []
    oos_turn = []
    test_start = train_days
    fold_id = 0

    while test_start < len(close):
        test_end = min(test_start + test_days, len(close))
        if test_end - test_start < max(20, min(test_days, 20)):
            break
        train_start = max(0, test_start - train_days)
        train_idx = close.index[train_start:test_start]
        test_idx = close.index[test_start:test_end]

        ranked = []
        for params, net, gross, turnover in cache:
            m = metrics(net.loc[train_idx], turnover.loc[train_idx])
            ranked.append((score(metric_name, m), params, net, gross, turnover, m))
        ranked.sort(key=lambda x: x[0], reverse=True)
        _, best_params, best_net, best_gross, best_turn, train_metrics = ranked[0]

        test_net = best_net.loc[test_idx]
        test_gross = best_gross.loc[test_idx]
        test_turn = best_turn.loc[test_idx]
        test_metrics = metrics(test_net, test_turn)

        folds.append({
            "fold": fold_id,
            "train_from": str(train_idx[0].date()),
            "train_to": str(train_idx[-1].date()),
            "test_from": str(test_idx[0].date()),
            "test_to": str(test_idx[-1].date()),
            "selected_params": best_params,
            "train_metrics": train_metrics,
            "test_metrics": test_metrics,
        })
        oos_net.append(test_net)
        oos_gross.append(test_gross)
        oos_turn.append(test_turn)
        test_start += step_days
        fold_id += 1

    if not oos_net:
        raise ValueError(f"No OOS folds produced for {module}")

    net = pd.concat(oos_net)
    gross = pd.concat(oos_gross)
    turn = pd.concat(oos_turn)
    net = net[~net.index.duplicated(keep="first")].sort_index()
    gross = gross.loc[net.index]
    turn = turn.loc[net.index]

    base_metrics = metrics(net, turn)
    benchmark = metrics(close.pct_change().fillna(0.0).loc[net.index])

    robust_cfg = request.get("robustness", {})
    recent_days = max(20, min(int(robust_cfg.get("recent_days", 126)), len(net)))
    recent_net = net.iloc[-recent_days:]
    recent_turn = turn.loc[recent_net.index]

    one_way = (cost_bps + slippage_bps) / 10_000.0
    cost_stress = {}
    for mult in [1.0, 1.5, 2.0]:
        stressed = gross - turn * one_way * mult
        cost_stress[f"{mult:.1f}x"] = metrics(stressed, turn)

    positive_folds = sum(1 for x in folds if x["test_metrics"]["total_return"] > 0.0)
    bootstrap_cfg = robust_cfg.get("bootstrap", {})
    bootstrap = bootstrap_summary(
        net,
        int(bootstrap_cfg.get("block_days", 5)),
        int(bootstrap_cfg.get("samples", 1000)),
        int(bootstrap_cfg.get("seed", 42)),
    )
    regimes = regime_analysis(close, net, int(robust_cfg.get("min_regime_days", 40)))

    robustness = {
        "recent": {"days": recent_days, "metrics": metrics(recent_net, recent_turn)},
        "fold_stability": {
            "folds": len(folds),
            "positive_folds": positive_folds,
            "positive_fold_ratio": float(positive_folds / len(folds)),
            "median_fold_return": float(np.median([x["test_metrics"]["total_return"] for x in folds])),
            "worst_fold_return": float(np.min([x["test_metrics"]["total_return"] for x in folds])),
        },
        "cost_stress": cost_stress,
        "bootstrap": bootstrap,
        "regime_analysis": regimes,
        "benchmark_comparison": {
            "strategy_total_return": float(base_metrics["total_return"]),
            "benchmark_total_return": float(benchmark["total_return"]),
            "excess_total_return": float(base_metrics["total_return"] - benchmark["total_return"]),
            "strategy_sharpe": float(base_metrics["sharpe"]),
            "benchmark_sharpe": float(benchmark["sharpe"]),
        },
    }

    rules = request.get("validation", {})
    checks = {
        "oos_total_return": base_metrics["total_return"] >= float(rules.get("min_oos_total_return", 0.0)),
        "oos_sharpe": base_metrics["sharpe"] >= float(rules.get("min_oos_sharpe", 0.0)),
        "positive_fold_ratio": robustness["fold_stability"]["positive_fold_ratio"] >= float(
            rules.get("min_positive_fold_ratio", 0.5)
        ),
        "positive_recent": (
            robustness["recent"]["metrics"]["total_return"] > 0.0
            if bool(rules.get("require_positive_recent", True))
            else True
        ),
        "positive_at_2x_cost": (
            robustness["cost_stress"]["2.0x"]["total_return"] > 0.0
            if bool(rules.get("require_positive_at_2x_cost", True))
            else True
        ),
        "bootstrap_probability": robustness["bootstrap"]["prob_mean_daily_return_positive"] >= float(
            rules.get("min_bootstrap_positive_probability", 0.55)
        ),
        "positive_regime_ratio": robustness["regime_analysis"]["positive_regime_ratio"] >= float(
            rules.get("min_positive_regime_ratio", 0.5)
        ),
        "max_drawdown": base_metrics["max_drawdown"] >= float(rules.get("max_drawdown_floor", -1.0)),
    }
    passed = all(checks.values())

    return {
        "module": module,
        "status": "PASS_CANDIDATE" if passed else "FAIL",
        "second_engine_eligible": bool(passed),
        "oos_metrics": base_metrics,
        "benchmark": benchmark,
        "folds": folds,
        "robustness": robustness,
        "validation_checks": checks,
    }


def report(result: dict) -> str:
    lines = [
        f"# JNU V2.2 Daily Proxy Suite: {result['request_id']}",
        "",
        f"- Data: {result['data']['date_from']} -> {result['data']['date_to']} ({result['data']['observations']} observations)",
        f"- VectorBT: {result['engine']['vectorbt_version']}",
        f"- Candidate modules: {len(result['modules'])}",
        f"- Eligible for second engine: {len(result['second_engine_queue'])}",
        "",
        "## Summary",
        "",
        "| Module | Status | OOS return | Sharpe | Max DD | Recent | 2x cost | +folds | +regimes | Bootstrap P+ |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for m in result["modules"]:
        o = m["oos_metrics"]
        r = m["robustness"]
        lines.append(
            f"| {m['module']} | {m['status']} | {o['total_return']:.2%} | {o['sharpe']:.3f} | "
            f"{o['max_drawdown']:.2%} | {r['recent']['metrics']['total_return']:.2%} | "
            f"{r['cost_stress']['2.0x']['total_return']:.2%} | "
            f"{r['fold_stability']['positive_fold_ratio']:.0%} | "
            f"{r['regime_analysis']['positive_regime_ratio']:.0%} | "
            f"{r['bootstrap']['prob_mean_daily_return_positive']:.1%} |"
        )
    lines += [
        "",
        "## Second-engine queue",
        "",
    ]
    if result["second_engine_queue"]:
        for item in result["second_engine_queue"]:
            lines.append(f"- {item}")
    else:
        lines.append("- None. Do not tune failures into passes; propose new hypotheses instead.")

    lines += [
        "",
        "## Interpretation limits",
        "",
        "- These are daily proxy tests, not JNU intraday validation.",
        "- NDX and USDJPY are aligned so their day-t observations can only affect the next Nikkei trading-day position.",
        "- Raw downloaded source files are cloud-cached and are not committed to Git.",
        "- A PASS_CANDIDATE is only eligible for a second engine; it is not a VALIDATED_JNU_MODULE.",
        "",
    ]
    return "\n".join(lines)


def run_request(request: dict) -> dict:
    if request.get("suite") != "jnu_v22_daily_proxy":
        raise ValueError("Unsupported suite")
    close, ext, sources = load_data(request)

    modules = [
        "trend_momentum",
        "breakout",
        "volatility_regime",
        "drawdown_repair",
        "relative_strength_ndx",
        "cross_market_confirmation",
    ]
    results = [evaluate_module(m, close, ext, request) for m in modules]
    queue = [m["module"] for m in results if m["second_engine_eligible"]]

    return {
        "request_id": request["request_id"],
        "status": "complete",
        "engine": {
            "name": "jnu-v22-daily-proxy-suite",
            "python_version": sys.version.split()[0],
            "numpy_version": np.__version__,
            "pandas_version": pd.__version__,
            "vectorbt_version": getattr(vbt, "__version__", "unknown"),
        },
        "data": {
            "date_from": str(close.index[0].date()),
            "date_to": str(close.index[-1].date()),
            "observations": int(len(close)),
            "sources": sources,
            "cache_policy": "same-day GitHub Actions cloud cache; raw files not committed",
        },
        "modules": results,
        "second_engine_queue": queue,
        "promotion_status": "CANDIDATE_SCREEN_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def process(path: Path) -> None:
    request_id = path.stem
    out_json = RESULTS / f"{request_id}.json"
    out_md = REPORTS / f"{request_id}.md"
    if out_json.exists():
        print(f"skip {request_id}: result exists")
        return
    request = json.loads(path.read_text(encoding="utf-8"))
    if request.get("request_id") != request_id:
        raise ValueError("request_id must match filename stem")
    result = run_request(request)
    RESULTS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(report(result), encoding="utf-8")
    print(f"completed {request_id}")


def main() -> int:
    REQUESTS.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    failures = []
    for path in sorted(REQUESTS.glob("*.json")):
        try:
            process(path)
        except Exception as exc:
            failures.append((path.name, str(exc)))
            traceback.print_exc()
    if failures:
        print(json.dumps({"failures": failures}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
