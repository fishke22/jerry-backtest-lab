from __future__ import annotations

import io
import itertools
import json
import math
import traceback
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kurtosis, norm, skew, ttest_1samp

ROOT = Path(__file__).resolve().parents[1]
REQUESTS = ROOT / "overfit_requests"
RESULTS = ROOT / "overfit_results"
REPORTS = ROOT / "overfit_reports"
CACHE = ROOT / ".cache" / "market-data"

NIKKEI_CACHE = CACHE / "nikkei_futures_daily.csv"
NDX_CACHE = CACHE / "fred_nasdaq100.csv"
FX_CACHE = CACHE / "fred_dexjpus.csv"


def parse_nikkei(raw: bytes) -> pd.Series:
    df = pd.read_csv(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
    dates = pd.to_datetime(df.iloc[:, 0], errors="coerce")
    values = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    s = pd.Series(values.to_numpy(), index=dates, name="close").dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


def parse_fred(raw: bytes, series_id: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
    date_col = "DATE" if "DATE" in df.columns else (
        "observation_date" if "observation_date" in df.columns else df.columns[0]
    )
    value_col = series_id if series_id in df.columns else df.columns[-1]
    dates = pd.to_datetime(df[date_col], errors="coerce")
    values = pd.to_numeric(df[value_col], errors="coerce")
    s = pd.Series(values.to_numpy(), index=dates, name=series_id).dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


def ensure_cache(meta: dict, path: Path) -> bytes:
    if path.exists():
        raw = path.read_bytes()
        import hashlib
        if hashlib.sha256(raw).hexdigest() == meta["sha256"]:
            return raw
    req = urllib.request.Request(meta["url"], headers={"User-Agent": "JerryBacktestLab/0.3"})
    with urllib.request.urlopen(req, timeout=120) as response:
        raw = response.read()
    import hashlib
    got = hashlib.sha256(raw).hexdigest()
    if got != meta["sha256"]:
        raise RuntimeError(f"Source snapshot changed: expected {meta['sha256']} got {got}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def sign_series(x: pd.Series) -> pd.Series:
    return pd.Series(np.sign(x.fillna(0.0)), index=x.index, dtype=float)


def volatility_regime_signal(close: pd.Series, params: dict) -> pd.Series:
    mom_lb = int(params["momentum_lookback"])
    vol_lb = int(params["vol_lookback"])
    regime = str(params["regime"])
    mom = close / close.shift(mom_lb) - 1.0
    rv = close.pct_change().rolling(vol_lb).std(ddof=0) * math.sqrt(252.0)
    rv_median = rv.rolling(126, min_periods=40).median()
    allowed = rv <= rv_median if regime == "low" else rv > rv_median
    return sign_series(mom).where(allowed, 0.0).fillna(0.0)


def cross_market_signal(
    close: pd.Series,
    ndx: pd.Series,
    usdjpy: pd.Series,
    params: dict,
) -> pd.Series:
    lb = int(params["lookback"])
    mode = str(params["mode"])
    j = sign_series(close / close.shift(lb) - 1.0)
    n = sign_series(ndx / ndx.shift(lb) - 1.0)
    f = sign_series(usdjpy / usdjpy.shift(lb) - 1.0)
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


def grid(module: str) -> list[dict]:
    if module == "volatility_regime":
        return [
            {"momentum_lookback": m, "vol_lookback": v, "regime": r}
            for m, v, r in itertools.product([20, 60], [20, 60], ["low", "high"])
        ]
    if module == "cross_market_confirmation":
        return [
            {"lookback": lb, "mode": mode}
            for lb, mode in itertools.product([10, 20, 60], ["majority", "unanimous"])
        ]
    raise ValueError(module)


def signal_for(
    module: str,
    close: pd.Series,
    ndx: pd.Series,
    usdjpy: pd.Series,
    params: dict,
) -> pd.Series:
    if module == "volatility_regime":
        return volatility_regime_signal(close, params)
    if module == "cross_market_confirmation":
        return cross_market_signal(close, ndx, usdjpy, params)
    raise ValueError(module)


def strategy_returns(
    close: pd.Series,
    signal: pd.Series,
    cost_bps: float,
    slippage_bps: float,
) -> pd.Series:
    pos = signal.shift(1).fillna(0.0).clip(-1.0, 1.0)
    market_ret = close.pct_change().fillna(0.0)
    turnover = pos.diff().abs()
    if len(turnover):
        turnover.iloc[0] = abs(pos.iloc[0])
    cost = (cost_bps + slippage_bps) / 10000.0
    return (pos * market_ret - turnover * cost).astype(float)


def sharpe(r: pd.Series) -> float:
    r = r.dropna().astype(float)
    if len(r) < 2:
        return 0.0
    sd = float(r.std(ddof=0))
    return float(r.mean() / sd * math.sqrt(252.0)) if sd > 0 else 0.0


def total_return(r: pd.Series) -> float:
    r = r.dropna().astype(float)
    return float((1.0 + r).prod() - 1.0) if len(r) else 0.0


def score(metric: str, r: pd.Series) -> float:
    return total_return(r) if metric == "total_return" else sharpe(r)


def split_groups(index: pd.DatetimeIndex, groups: int) -> list[np.ndarray]:
    return [x for x in np.array_split(np.arange(len(index)), groups) if len(x)]


def train_mask_with_purge_embargo(
    n: int,
    test_positions: np.ndarray,
    purge_days: int,
    embargo_days: int,
) -> np.ndarray:
    train = np.ones(n, dtype=bool)
    train[test_positions] = False
    test_set = set(int(x) for x in test_positions)
    segments = []
    start = None
    prev = None
    for x in sorted(test_set):
        if start is None or (prev is not None and x != prev + 1):
            if start is not None:
                segments.append((start, prev))
            start = x
        prev = x
    if start is not None:
        segments.append((start, prev))
    for a, b in segments:
        left = max(0, a - purge_days)
        right = min(n, b + embargo_days + 1)
        train[left:right] = False
    return train


def cpcv(
    returns_by_param: list[tuple[dict, pd.Series]],
    index: pd.DatetimeIndex,
    groups: int,
    test_groups: int,
    purge_days: int,
    embargo_days: int,
    selection_metric: str,
) -> dict:
    chunks = split_groups(index, groups)
    paths = []
    for combo in itertools.combinations(range(len(chunks)), test_groups):
        test_pos = np.concatenate([chunks[i] for i in combo])
        test_pos.sort()
        train_mask = train_mask_with_purge_embargo(
            len(index), test_pos, purge_days, embargo_days
        )
        train_idx = index[train_mask]
        test_idx = index[test_pos]
        ranked = []
        for params, r in returns_by_param:
            ranked.append((score(selection_metric, r.loc[train_idx]), params, r))
        ranked.sort(key=lambda x: x[0], reverse=True)
        _, params, chosen = ranked[0]
        test_r = chosen.loc[test_idx]
        paths.append({
            "test_groups": list(combo),
            "selected_params": params,
            "train_days": int(train_mask.sum()),
            "test_days": int(len(test_idx)),
            "test_total_return": total_return(test_r),
            "test_sharpe": sharpe(test_r),
        })
    positive = [p["test_total_return"] > 0 for p in paths]
    sharpes = [p["test_sharpe"] for p in paths]
    return {
        "paths": len(paths),
        "positive_paths": int(sum(positive)),
        "positive_path_ratio": float(np.mean(positive)),
        "median_sharpe": float(np.median(sharpes)),
        "worst_sharpe": float(np.min(sharpes)),
        "details": paths,
    }


def pbo(
    returns_by_param: list[tuple[dict, pd.Series]],
    index: pd.DatetimeIndex,
    slices: int,
    train_slices: int,
) -> dict:
    if slices % 2 != 0 or train_slices * 2 != slices:
        raise ValueError("PBO requires an even number of slices and half in-sample")
    chunks = split_groups(index, slices)
    combos = list(itertools.combinations(range(slices), train_slices))
    lambdas = []
    records = []
    seen = set()

    for combo in combos:
        comp = tuple(i for i in range(slices) if i not in combo)
        key = tuple(sorted((combo, comp)))
        if key in seen:
            continue
        seen.add(key)

        is_idx = index[np.concatenate([chunks[i] for i in combo])]
        oos_idx = index[np.concatenate([chunks[i] for i in comp])]

        in_scores = [sharpe(r.loc[is_idx]) for _, r in returns_by_param]
        best = int(np.argmax(in_scores))
        oos_scores = np.array([sharpe(r.loc[oos_idx]) for _, r in returns_by_param], dtype=float)

        # Percentile rank of the in-sample winner out of sample.
        order = np.argsort(np.argsort(oos_scores))
        percentile = float((order[best] + 1) / len(oos_scores))
        eps = 1e-9
        pct = min(max(percentile, eps), 1.0 - eps)
        lam = float(math.log(pct / (1.0 - pct)))
        lambdas.append(lam)
        records.append({
            "train_slices": list(combo),
            "selected_params": returns_by_param[best][0],
            "oos_percentile": percentile,
            "lambda": lam,
        })

    return {
        "splits": len(records),
        "pbo": float(np.mean(np.array(lambdas) <= 0.0)) if lambdas else 1.0,
        "median_lambda": float(np.median(lambdas)) if lambdas else float("-inf"),
        "details": records,
    }


def dsr(
    selected_returns: pd.Series,
    all_trial_returns: list[pd.Series],
) -> dict:
    r = selected_returns.dropna().astype(float)
    sr = sharpe(r) / math.sqrt(252.0)  # daily Sharpe
    trial_srs = np.array([sharpe(x) / math.sqrt(252.0) for x in all_trial_returns], dtype=float)
    n_trials = max(2, len(trial_srs))
    sr_std = float(np.std(trial_srs, ddof=1)) if len(trial_srs) > 1 else 0.0
    gamma = 0.5772156649015329
    expected_max_sr = sr_std * (
        (1.0 - gamma) * norm.ppf(1.0 - 1.0 / n_trials)
        + gamma * norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    )
    sk = float(skew(r, bias=False)) if len(r) > 2 else 0.0
    ku = float(kurtosis(r, fisher=False, bias=False)) if len(r) > 3 else 3.0
    denom_sq = 1.0 - sk * sr + ((ku - 1.0) / 4.0) * (sr ** 2)
    denom = math.sqrt(max(1e-12, denom_sq))
    z = (sr - expected_max_sr) * math.sqrt(max(1, len(r) - 1)) / denom
    probability = float(norm.cdf(z))
    return {
        "trials": int(n_trials),
        "observations": int(len(r)),
        "selected_annualized_sharpe": float(sharpe(r)),
        "expected_max_annualized_sharpe": float(expected_max_sr * math.sqrt(252.0)),
        "skew": sk,
        "kurtosis": ku,
        "dsr_probability": probability,
    }


def holm_bonferroni(p_values: dict[str, float], alpha: float) -> dict:
    ordered = sorted(p_values.items(), key=lambda kv: kv[1])
    decisions = {k: False for k in p_values}
    adjusted = {}
    running_max = 0.0
    m = len(ordered)
    stop = False
    for rank, (name, p) in enumerate(ordered, start=1):
        adj = min(1.0, (m - rank + 1) * p)
        running_max = max(running_max, adj)
        adjusted[name] = running_max
        threshold = alpha / (m - rank + 1)
        if not stop and p <= threshold:
            decisions[name] = True
        else:
            stop = True
            decisions[name] = False
    return {
        "alpha": alpha,
        "raw_p_values": p_values,
        "holm_adjusted_p_values": adjusted,
        "reject_null_positive_mean": decisions,
    }


def stitched_walk_forward_returns(
    module_result: dict,
    module: str,
    close: pd.Series,
    ndx: pd.Series,
    usdjpy: pd.Series,
    cost_bps: float,
    slippage_bps: float,
) -> pd.Series:
    out = []
    for fold in module_result["folds"]:
        params = fold["selected_params"]
        signal = signal_for(module, close, ndx, usdjpy, params)
        r = strategy_returns(close, signal, cost_bps, slippage_bps)
        idx = close.loc[fold["test_from"]:fold["test_to"]].index
        out.append(r.loc[idx])
    combined = pd.concat(out)
    return combined[~combined.index.duplicated(keep="first")].sort_index()


def evaluate_module(
    module_result: dict,
    close: pd.Series,
    ndx: pd.Series,
    usdjpy: pd.Series,
    request: dict,
) -> dict:
    module = module_result["module"]
    cost_bps = float(request["cost_bps"])
    slippage_bps = float(request["slippage_bps"])

    param_returns = []
    for params in grid(module):
        sig = signal_for(module, close, ndx, usdjpy, params)
        r = strategy_returns(close, sig, cost_bps, slippage_bps)
        param_returns.append((params, r))

    oos = stitched_walk_forward_returns(
        module_result, module, close, ndx, usdjpy, cost_bps, slippage_bps
    )
    oos_index = oos.index
    param_returns_oos = [(p, r.loc[oos_index]) for p, r in param_returns]

    c = request["cpcv"]
    cpcv_result = cpcv(
        param_returns_oos,
        oos_index,
        int(c["groups"]),
        int(c["test_groups"]),
        int(c["purge_days"]),
        int(c["embargo_days"]),
        str(c.get("selection_metric", "sharpe")),
    )

    p = request["pbo"]
    pbo_result = pbo(
        param_returns_oos,
        oos_index,
        int(p["slices"]),
        int(p["train_slices"]),
    )

    dsr_result = dsr(oos, [r for _, r in param_returns_oos])

    # One-sided p-value for mean return > 0, later Holm-adjusted across surviving modules.
    t = ttest_1samp(oos.to_numpy(dtype=float), popmean=0.0, alternative="greater")
    one_sided_p = float(t.pvalue) if np.isfinite(t.pvalue) else 1.0

    return {
        "module": module,
        "cpcv": cpcv_result,
        "pbo": pbo_result,
        "dsr": dsr_result,
        "one_sided_mean_return_p": one_sided_p,
    }


def report_md(result: dict) -> str:
    lines = [
        f"# JNU V2.2 overfit / multiple-testing validation: {result['request_id']}",
        "",
        f"- Overall status: **{result['overall_status']}**",
        f"- Source first engine: {result['source_suite_result']}",
        f"- Source second engine: {result['source_second_engine_result']}",
        "",
        "| Module | CPCV +paths | CPCV median Sharpe | PBO | DSR P | Holm adj p | Final |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    holm = result["multiple_testing"]["holm"]["holm_adjusted_p_values"]
    for m in result["modules"]:
        lines.append(
            f"| {m['module']} | {m['cpcv']['positive_path_ratio']:.1%} | "
            f"{m['cpcv']['median_sharpe']:.3f} | {m['pbo']['pbo']:.1%} | "
            f"{m['dsr']['dsr_probability']:.1%} | {holm[m['module']]:.4f} | "
            f"{m['status']} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- CPCV uses purging and embargo around held-out groups before parameter selection.",
        "- PBO measures how often the in-sample winner falls into the lower half out-of-sample.",
        "- DSR discounts Sharpe for non-normal returns and the number/dispersion of tried parameter configurations.",
        "- Holm-Bonferroni controls family-wise error across the surviving modules.",
        "- This stage intentionally does not search a wider parameter grid to rescue failures.",
        "",
    ]
    return "\n".join(lines)


def process(path: Path) -> None:
    request_id = path.stem
    out_json = RESULTS / f"{request_id}.json"
    out_md = REPORTS / f"{request_id}.md"
    if out_json.exists():
        print(f"skip {request_id}: result exists")
        return

    request = json.loads(path.read_text(encoding="utf-8"))
    suite = json.loads((ROOT / request["source_suite_result"]).read_text(encoding="utf-8"))
    second = json.loads((ROOT / request["source_second_engine_result"]).read_text(encoding="utf-8"))

    if request.get("require_second_engine_pass", True):
        if second.get("overall_status") != "PASS_SECOND_ENGINE":
            raise ValueError("Second engine did not pass")

    wanted = set(request["modules"])
    source_modules = {m["module"]: m for m in suite["modules"] if m["module"] in wanted}
    if set(source_modules) != wanted:
        raise ValueError("Missing module in source suite")

    second_ok = {
        m["module"]
        for m in second["modules"]
        if m.get("status") == "PASS_ENGINE_REPLAY"
    }
    if not wanted.issubset(second_ok):
        raise ValueError("A requested module did not pass Nautilus replay")

    src = suite["data"]["sources"]
    nk = parse_nikkei(ensure_cache(src["nikkei_futures"], NIKKEI_CACHE))
    ndx_raw = parse_fred(ensure_cache(src["nasdaq100_fred"], NDX_CACHE), "NASDAQ100")
    fx_raw = parse_fred(ensure_cache(src["usdjpy_fred"], FX_CACHE), "DEXJPUS")

    start = pd.Timestamp(suite["data"]["date_from"])
    end = pd.Timestamp(suite["data"]["date_to"])
    close = nk.loc[start:end]
    ndx = ndx_raw.reindex(close.index).ffill()
    usdjpy = fx_raw.reindex(close.index).ffill()

    module_results = [
        evaluate_module(source_modules[name], close, ndx, usdjpy, request)
        for name in request["modules"]
    ]

    mt = request["multiple_testing"]
    pvals = {m["module"]: m["one_sided_mean_return_p"] for m in module_results}
    holm = holm_bonferroni(pvals, float(mt["holm_alpha"]))

    rules = request["validation"]
    final_modules = []
    for m in module_results:
        checks = {
            "cpcv_positive_path_ratio": m["cpcv"]["positive_path_ratio"]
            >= float(rules["min_cpcv_positive_path_ratio"]),
            "cpcv_median_sharpe": m["cpcv"]["median_sharpe"]
            >= float(rules["min_cpcv_median_sharpe"]),
            "pbo": m["pbo"]["pbo"] <= float(rules["max_pbo"]),
            "dsr": (
                m["dsr"]["dsr_probability"] >= float(mt["dsr_probability_min"])
                if rules.get("require_dsr_pass", True)
                else True
            ),
            "holm": (
                bool(holm["reject_null_positive_mean"][m["module"]])
                if rules.get("require_holm_pass", True)
                else True
            ),
        }
        passed = all(checks.values())
        final_modules.append({
            **m,
            "checks": checks,
            "status": "PASS_OVERFIT_GATES" if passed else "FAIL_OVERFIT_GATES",
        })

    survivors = [m["module"] for m in final_modules if m["status"] == "PASS_OVERFIT_GATES"]
    overall = "PASS_OVERFIT_STAGE" if survivors else "NO_MODULE_PASSED_OVERFIT_STAGE"

    result = {
        "request_id": request_id,
        "status": "complete",
        "overall_status": overall,
        "source_suite_result": request["source_suite_result"],
        "source_second_engine_result": request["source_second_engine_result"],
        "modules": final_modules,
        "multiple_testing": {"holm": holm},
        "survivors": survivors,
        "promotion_status": "OVERFIT_SCREEN_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    RESULTS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(report_md(result), encoding="utf-8")
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
        print(json.dumps({"failures": failures}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
