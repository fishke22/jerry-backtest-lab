from __future__ import annotations

import hashlib
import io
import json
import math
import sys
import traceback
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt

ROOT = Path(__file__).resolve().parents[1]
REQUESTS = ROOT / "requests"
RESULTS = ROOT / "results"
REPORTS = ROOT / "reports"

NIKKEI_FUTURES_CSV = (
    "https://indexes.nikkei.co.jp/nkave/historical/"
    "nikkei_225_futures_index_series_daily_en.csv"
)


@dataclass(frozen=True)
class SourceData:
    close: pd.Series
    source_sha256: str
    source_url: str


def fetch_nikkei_futures_index() -> SourceData:
    req = urllib.request.Request(
        NIKKEI_FUTURES_CSV,
        headers={"User-Agent": "JerryBacktestLab/0.1"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()

    text = raw.decode("utf-8-sig", errors="replace")
    df = pd.read_csv(io.StringIO(text))
    if df.shape[1] < 2:
        raise RuntimeError("Unexpected Nikkei Futures Index CSV shape")

    date_col = df.columns[0]
    value_col = df.columns[1]
    dates = pd.to_datetime(df[date_col], errors="coerce")
    values = pd.to_numeric(df[value_col], errors="coerce")
    series = pd.Series(values.to_numpy(), index=dates, name="close").dropna()
    series = series[~series.index.duplicated(keep="last")].sort_index()

    if series.empty:
        raise RuntimeError("Nikkei Futures Index source returned no valid rows")

    return SourceData(
        close=series,
        source_sha256=hashlib.sha256(raw).hexdigest(),
        source_url=NIKKEI_FUTURES_CSV,
    )


def sliced_close(source: SourceData, request: dict) -> pd.Series:
    close = source.close
    date_from = request.get("date_from")
    date_to = request.get("date_to")
    if date_from:
        close = close.loc[pd.Timestamp(date_from):]
    if date_to:
        close = close.loc[:pd.Timestamp(date_to)]
    if len(close) < 50:
        raise ValueError("Selected date range is too short for a meaningful daily backtest")
    return close


def sma_signal(close: pd.Series, fast: int, slow: int, allow_short: bool) -> pd.Series:
    if fast <= 0 or slow <= 0 or fast >= slow:
        raise ValueError("Require 0 < fast_window < slow_window")

    fast_ma = vbt.MA.run(close, window=fast).ma
    slow_ma = vbt.MA.run(close, window=slow).ma
    valid = fast_ma.notna() & slow_ma.notna()

    if allow_short:
        signal = pd.Series(
            np.where(valid, np.where(fast_ma > slow_ma, 1.0, -1.0), 0.0),
            index=close.index,
            dtype=float,
        )
    else:
        signal = pd.Series(
            np.where(valid & (fast_ma > slow_ma), 1.0, 0.0),
            index=close.index,
            dtype=float,
        )
    return signal


def strategy_returns(
    close: pd.Series,
    fast: int,
    slow: int,
    allow_short: bool,
    cost_bps: float,
    slippage_bps: float,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    signal = sma_signal(close, fast, slow, allow_short)
    position = signal.shift(1).fillna(0.0)
    market_ret = close.pct_change().fillna(0.0)

    turnover = position.diff().abs()
    if len(turnover):
        turnover.iloc[0] = abs(position.iloc[0])

    one_way_cost = (float(cost_bps) + float(slippage_bps)) / 10_000.0
    net_ret = position * market_ret - turnover * one_way_cost
    return net_ret.astype(float), position, turnover.astype(float)


def metrics(returns: pd.Series, turnover: pd.Series | None = None) -> dict:
    r = returns.dropna().astype(float)
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
    annualized_return = (
        float(equity.iloc[-1] ** (1.0 / years) - 1.0)
        if years > 0 and equity.iloc[-1] > 0
        else -1.0
    )
    std = float(r.std(ddof=0))
    ann_vol = std * math.sqrt(252.0)
    sharpe = float(r.mean() / std * math.sqrt(252.0)) if std > 0 else 0.0
    drawdown = equity / equity.cummax() - 1.0
    nonzero = r[r != 0.0]
    hit_rate = float((nonzero > 0).mean()) if len(nonzero) else 0.0

    return {
        "days": int(len(r)),
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": ann_vol,
        "sharpe": sharpe,
        "max_drawdown": float(drawdown.min()),
        "hit_rate": hit_rate,
        "turnover": float(turnover.loc[r.index].sum()) if turnover is not None else 0.0,
    }


def block_bootstrap_summary(
    returns: pd.Series,
    block_days: int = 5,
    samples: int = 1000,
    seed: int = 42,
) -> dict:
    r = returns.dropna().astype(float).to_numpy()
    n = len(r)
    if n < 20:
        return {
            "block_days": int(block_days),
            "samples": int(samples),
            "mean_daily_return_ci_95": [0.0, 0.0],
            "prob_mean_daily_return_positive": 0.0,
        }

    block_days = max(1, min(int(block_days), n))
    samples = max(100, int(samples))
    rng = np.random.default_rng(int(seed))
    starts = np.arange(0, n - block_days + 1)
    means = np.empty(samples, dtype=float)

    for i in range(samples):
        sampled = []
        while len(sampled) < n:
            start = int(rng.choice(starts))
            sampled.extend(r[start : start + block_days])
        means[i] = float(np.mean(sampled[:n]))

    low, high = np.quantile(means, [0.025, 0.975])
    return {
        "block_days": int(block_days),
        "samples": int(samples),
        "mean_daily_return_ci_95": [float(low), float(high)],
        "prob_mean_daily_return_positive": float(np.mean(means > 0.0)),
    }


def candidate_score(metric_name: str, m: dict) -> float:
    if metric_name == "total_return":
        return float(m["total_return"])
    if metric_name == "annualized_return":
        return float(m["annualized_return"])
    return float(m["sharpe"])


def fixed_backtest(close: pd.Series, request: dict) -> dict:
    fast = int(request.get("fast_window", 10))
    slow = int(request.get("slow_window", 50))
    net_ret, position, turnover = strategy_returns(
        close,
        fast,
        slow,
        bool(request.get("allow_short", True)),
        float(request.get("cost_bps", 0.0)),
        float(request.get("slippage_bps", 0.0)),
    )
    return {
        "mode": "fixed",
        "parameters": {"fast_window": fast, "slow_window": slow},
        "metrics": metrics(net_ret, turnover),
        "benchmark": metrics(close.pct_change().fillna(0.0)),
    }


def walk_forward(close: pd.Series, request: dict) -> dict:
    wf = request.get("walk_forward", {})
    train_days = int(wf.get("train_days", 252))
    test_days = int(wf.get("test_days", 63))
    step_days = int(wf.get("step_days", test_days))
    fast_windows = [int(x) for x in wf.get("fast_windows", [5, 10, 20])]
    slow_windows = [int(x) for x in wf.get("slow_windows", [40, 60, 100, 150])]
    selection_metric = str(wf.get("selection_metric", "sharpe"))
    allow_short = bool(request.get("allow_short", True))
    cost_bps = float(request.get("cost_bps", 0.0))
    slippage_bps = float(request.get("slippage_bps", 0.0))

    combos = [(f, s) for f in fast_windows for s in slow_windows if 0 < f < s]
    if not combos:
        raise ValueError("No valid fast/slow window combinations")
    if len(close) < train_days + test_days:
        raise ValueError("Not enough observations for requested walk-forward windows")

    cached: dict[tuple[int, int], tuple[pd.Series, pd.Series]] = {}
    for fast, slow in combos:
        ret, _, turnover = strategy_returns(
            close, fast, slow, allow_short, cost_bps, slippage_bps
        )
        cached[(fast, slow)] = (ret, turnover)

    folds = []
    oos_returns = []
    oos_turnover = []

    test_start = train_days
    fold_id = 0
    while test_start < len(close):
        test_end = min(test_start + test_days, len(close))
        if test_end - test_start < max(5, min(test_days, 20)):
            break

        train_start = max(0, test_start - train_days)
        train_idx = close.index[train_start:test_start]
        test_idx = close.index[test_start:test_end]

        ranked = []
        for fast, slow in combos:
            ret, turnover = cached[(fast, slow)]
            m = metrics(ret.loc[train_idx], turnover.loc[train_idx])
            ranked.append((candidate_score(selection_metric, m), fast, slow, m))

        ranked.sort(key=lambda x: x[0], reverse=True)
        _, best_fast, best_slow, train_metrics = ranked[0]
        best_ret, best_turnover = cached[(best_fast, best_slow)]
        test_ret = best_ret.loc[test_idx]
        test_turn = best_turnover.loc[test_idx]
        test_metrics = metrics(test_ret, test_turn)

        folds.append(
            {
                "fold": fold_id,
                "train_from": str(train_idx[0].date()),
                "train_to": str(train_idx[-1].date()),
                "test_from": str(test_idx[0].date()),
                "test_to": str(test_idx[-1].date()),
                "selected": {
                    "fast_window": best_fast,
                    "slow_window": best_slow,
                    "selection_metric": selection_metric,
                },
                "train_metrics": train_metrics,
                "test_metrics": test_metrics,
            }
        )
        oos_returns.append(test_ret)
        oos_turnover.append(test_turn)
        fold_id += 1
        test_start += step_days

    if not oos_returns:
        raise ValueError("Walk-forward generated no OOS folds")

    combined_ret = pd.concat(oos_returns)
    combined_turn = pd.concat(oos_turnover)
    combined_ret = combined_ret[~combined_ret.index.duplicated(keep="first")].sort_index()
    combined_turn = combined_turn.loc[combined_ret.index]

    bench = close.pct_change().fillna(0.0).loc[combined_ret.index]
    oos_metrics = metrics(combined_ret, combined_turn)
    benchmark_metrics = metrics(bench)

    recent_days = int(request.get("robustness", {}).get("recent_days", 126))
    recent_days = max(20, min(recent_days, len(combined_ret)))
    recent_ret = combined_ret.iloc[-recent_days:]
    recent_turn = combined_turn.loc[recent_ret.index]

    base_one_way_cost = (cost_bps + slippage_bps) / 10_000.0
    cost_stress = {}
    for multiplier in [1.0, 1.5, 2.0]:
        stressed = combined_ret - combined_turn * base_one_way_cost * (multiplier - 1.0)
        cost_stress[f"{multiplier:.1f}x"] = metrics(stressed, combined_turn)

    positive_folds = sum(
        1 for fold in folds if float(fold["test_metrics"]["total_return"]) > 0.0
    )
    fold_returns = [float(fold["test_metrics"]["total_return"]) for fold in folds]
    fold_sharpes = [float(fold["test_metrics"]["sharpe"]) for fold in folds]

    bootstrap_cfg = request.get("robustness", {}).get("bootstrap", {})
    bootstrap = block_bootstrap_summary(
        combined_ret,
        block_days=int(bootstrap_cfg.get("block_days", 5)),
        samples=int(bootstrap_cfg.get("samples", 1000)),
        seed=int(bootstrap_cfg.get("seed", 42)),
    )

    robustness = {
        "recent": {
            "days": recent_days,
            "metrics": metrics(recent_ret, recent_turn),
        },
        "fold_stability": {
            "folds": len(folds),
            "positive_folds": positive_folds,
            "positive_fold_ratio": float(positive_folds / len(folds)),
            "median_fold_return": float(np.median(fold_returns)),
            "worst_fold_return": float(np.min(fold_returns)),
            "median_fold_sharpe": float(np.median(fold_sharpes)),
        },
        "cost_stress": cost_stress,
        "benchmark_comparison": {
            "strategy_total_return": float(oos_metrics["total_return"]),
            "benchmark_total_return": float(benchmark_metrics["total_return"]),
            "excess_total_return": float(
                oos_metrics["total_return"] - benchmark_metrics["total_return"]
            ),
            "strategy_sharpe": float(oos_metrics["sharpe"]),
            "benchmark_sharpe": float(benchmark_metrics["sharpe"]),
            "sharpe_delta": float(
                oos_metrics["sharpe"] - benchmark_metrics["sharpe"]
            ),
        },
        "block_bootstrap": bootstrap,
    }

    return {
        "mode": "walk_forward",
        "settings": {
            "train_days": train_days,
            "test_days": test_days,
            "step_days": step_days,
            "fast_windows": fast_windows,
            "slow_windows": slow_windows,
            "selection_metric": selection_metric,
        },
        "folds": folds,
        "oos_metrics": oos_metrics,
        "oos_benchmark": benchmark_metrics,
        "robustness": robustness,
    }


def validation_status(result: dict, request: dict) -> dict:
    rules = request.get("validation", {})
    m = result.get("oos_metrics") or result.get("metrics") or {}
    robustness = result.get("robustness") or {}

    checks = {
        "min_oos_sharpe": float(m.get("sharpe", 0.0))
        >= float(rules.get("min_oos_sharpe", 0.0)),
        "min_oos_total_return": float(m.get("total_return", 0.0))
        >= float(rules.get("min_oos_total_return", 0.0)),
        "min_oos_days": int(m.get("days", 0)) >= int(rules.get("min_oos_days", 1)),
    }
    if bool(rules.get("require_positive_after_cost", True)):
        checks["positive_after_cost"] = float(m.get("total_return", 0.0)) > 0.0

    if robustness:
        fold_ratio = float(
            robustness.get("fold_stability", {}).get("positive_fold_ratio", 0.0)
        )
        recent_total = float(
            robustness.get("recent", {}).get("metrics", {}).get("total_return", 0.0)
        )
        cost_2x_total = float(
            robustness.get("cost_stress", {})
            .get("2.0x", {})
            .get("total_return", 0.0)
        )
        bootstrap_prob = float(
            robustness.get("block_bootstrap", {})
            .get("prob_mean_daily_return_positive", 0.0)
        )
        excess_total = float(
            robustness.get("benchmark_comparison", {})
            .get("excess_total_return", 0.0)
        )

        checks["min_positive_fold_ratio"] = fold_ratio >= float(
            rules.get("min_positive_fold_ratio", 0.5)
        )
        if bool(rules.get("require_positive_recent", True)):
            checks["positive_recent"] = recent_total > 0.0
        if bool(rules.get("require_positive_at_2x_cost", True)):
            checks["positive_at_2x_cost"] = cost_2x_total > 0.0
        checks["min_bootstrap_positive_probability"] = bootstrap_prob >= float(
            rules.get("min_bootstrap_positive_probability", 0.5)
        )
        if "min_excess_total_return" in rules:
            checks["min_excess_total_return"] = excess_total >= float(
                rules["min_excess_total_return"]
            )

    return {
        "mechanical_status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "promotion_status": "CANDIDATE_ONLY",
        "note": (
            "PASS is not equivalent to VALIDATED_JNU_MODULE. "
            "Independent review, regime analysis, leakage checks, and second-engine "
            "confirmation are still required before promotion."
        ),
    }


def run_request(request: dict) -> dict:
    if request.get("instrument") != "nikkei225_futures_index":
        raise ValueError("Phase 1 supports only instrument=nikkei225_futures_index")
    if request.get("strategy") != "sma_cross":
        raise ValueError("Phase 1 supports only strategy=sma_cross")

    source = fetch_nikkei_futures_index()
    close = sliced_close(source, request)

    wf = request.get("walk_forward", {})
    if bool(wf.get("enabled", False)):
        core = walk_forward(close, request)
    else:
        core = fixed_backtest(close, request)

    result = {
        "request_id": request["request_id"],
        "status": "complete",
        "engine": {
            "name": "jerry-backtest-lab-phase1",
            "vectorbt_version": getattr(vbt, "__version__", "unknown"),
            "numpy_version": getattr(np, "__version__", "unknown"),
            "pandas_version": getattr(pd, "__version__", "unknown"),
            "python_version": sys.version.split()[0],
        },
        "instrument": {
            "name": "Nikkei 225 Futures Index",
            "role": "daily proxy for JNU/Nikkei futures directional modules",
        },
        "data": {
            "source": "Nikkei Indexes official CSV",
            "source_url": source.source_url,
            "source_sha256": source.source_sha256,
            "date_from": str(close.index[0].date()),
            "date_to": str(close.index[-1].date()),
            "observations": int(len(close)),
            "raw_data_committed": False,
        },
        "cost_model": {
            "commission_bps_per_position_unit": float(request.get("cost_bps", 0.0)),
            "slippage_bps_per_position_unit": float(request.get("slippage_bps", 0.0)),
        },
        "backtest": core,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    result["validation"] = validation_status(core, request)
    return result


def report_markdown(result: dict) -> str:
    bt = result["backtest"]
    m = bt.get("oos_metrics") or bt.get("metrics")
    b = bt.get("oos_benchmark") or bt.get("benchmark")
    val = result["validation"]

    lines = [
        f"# Backtest: {result['request_id']}",
        "",
        f"- Status: **{result['status']}**",
        f"- Mechanical validation: **{val['mechanical_status']}**",
        f"- Promotion status: **{val['promotion_status']}**",
        f"- Data: {result['data']['date_from']} → {result['data']['date_to']} "
        f"({result['data']['observations']} observations)",
        f"- VectorBT: {result['engine']['vectorbt_version']}",
        "",
        "## Strategy metrics",
        "",
        f"- Total return: {m['total_return']:.2%}",
        f"- Annualized return: {m['annualized_return']:.2%}",
        f"- Annualized volatility: {m['annualized_volatility']:.2%}",
        f"- Sharpe: {m['sharpe']:.3f}",
        f"- Max drawdown: {m['max_drawdown']:.2%}",
        f"- Hit rate: {m['hit_rate']:.2%}",
        f"- Turnover: {m['turnover']:.2f}",
        "",
        "## Benchmark over the same evaluation dates",
        "",
        f"- Total return: {b['total_return']:.2%}",
        f"- Sharpe: {b['sharpe']:.3f}",
        f"- Max drawdown: {b['max_drawdown']:.2%}",
        "",
        "## Validation checks",
        "",
    ]
    for key, passed in val["checks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} — {key}")

    robustness = bt.get("robustness") or {}
    if robustness:
        recent = robustness["recent"]["metrics"]
        stability = robustness["fold_stability"]
        comparison = robustness["benchmark_comparison"]
        bootstrap = robustness["block_bootstrap"]
        cost2 = robustness["cost_stress"]["2.0x"]
        lines += [
            "",
            "## Robustness",
            "",
            f"- Recent {robustness['recent']['days']} OOS days return: {recent['total_return']:.2%}",
            f"- Positive fold ratio: {stability['positive_fold_ratio']:.1%}",
            f"- Worst fold return: {stability['worst_fold_return']:.2%}",
            f"- 2× cost total return: {cost2['total_return']:.2%}",
            f"- Excess total return vs benchmark: {comparison['excess_total_return']:.2%}",
            f"- Bootstrap P(mean daily return > 0): {bootstrap['prob_mean_daily_return_positive']:.1%}",
        ]

    if bt.get("folds"):
        lines += ["", "## Walk-forward folds", ""]
        for fold in bt["folds"]:
            p = fold["selected"]
            tm = fold["test_metrics"]
            lines.append(
                f"- Fold {fold['fold']}: {fold['test_from']} → {fold['test_to']} | "
                f"fast={p['fast_window']} slow={p['slow_window']} | "
                f"OOS return={tm['total_return']:.2%} Sharpe={tm['sharpe']:.3f}"
            )

    lines += [
        "",
        "## Interpretation limit",
        "",
        "This is a daily Futures Index proxy test. It does not validate JNU-specific "
        "night-session, intraday volume-profile, basis, roll-spread, OI, or micro-liquidity modules.",
        "",
    ]
    return "\n".join(lines)


def process(path: Path) -> None:
    request_id = path.stem
    result_path = RESULTS / f"{request_id}.json"
    report_path = REPORTS / f"{request_id}.md"
    if result_path.exists():
        print(f"skip {request_id}: result already exists")
        return

    request = json.loads(path.read_text(encoding="utf-8"))
    if request.get("request_id") != request_id:
        raise ValueError(
            f"request_id must exactly match filename stem: {request_id}"
        )

    result = run_request(request)
    RESULTS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(report_markdown(result), encoding="utf-8")
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
