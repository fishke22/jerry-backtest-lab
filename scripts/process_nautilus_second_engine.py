from __future__ import annotations

import hashlib
import io
import json
import math
import re
import sys
import time
import traceback
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import LoggingConfig
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.currencies import JPY
from nautilus_trader.model.data import Bar
from nautilus_trader.model.data import BarType
from nautilus_trader.model.enums import AccountType
from nautilus_trader.model.enums import AssetClass
from nautilus_trader.model.enums import OmsType
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.identifiers import Symbol
from nautilus_trader.model.identifiers import TraderId
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.instruments import PerpetualContract
from nautilus_trader.model.objects import Money
from nautilus_trader.model.objects import Price
from nautilus_trader.model.objects import Quantity
from nautilus_trader.persistence.wranglers import BarDataWrangler
from nautilus_trader.trading.strategy import Strategy

ROOT = Path(__file__).resolve().parents[1]
REQUESTS = ROOT / "nautilus_requests"
RESULTS = ROOT / "nautilus_results"
REPORTS = ROOT / "nautilus_reports"
CACHE = ROOT / ".cache" / "market-data"

CACHE_NAMES = {
    "nikkei_futures": "nikkei_futures_daily.csv",
    "nasdaq100_fred": "fred_nasdaq100.csv",
    "usdjpy_fred": "fred_dexjpus.csv",
}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def get_bytes(url: str, cache_name: str, expected_sha: str) -> tuple[bytes, bool]:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / cache_name
    if path.exists():
        raw = path.read_bytes()
        if digest(raw) == expected_sha:
            return raw, True

    last_error: Exception | None = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 JerryBacktestLab-Nautilus/0.1",
                    "Accept": "text/csv,*/*;q=0.8",
                },
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                raw = response.read()
            if digest(raw) != expected_sha:
                raise RuntimeError(
                    f"Source hash changed for {cache_name}: "
                    f"expected {expected_sha}, got {digest(raw)}"
                )
            path.write_bytes(raw)
            return raw, False
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Could not obtain exact source snapshot {cache_name}: {last_error}")


def parse_nikkei(raw: bytes) -> pd.Series:
    df = pd.read_csv(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
    dates = pd.to_datetime(df.iloc[:, 0], errors="coerce", utc=True)
    values = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    s = pd.Series(values.to_numpy(), index=dates, name="close").dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


def parse_fred(raw: bytes, series_id: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
    date_col = "DATE" if "DATE" in df.columns else (
        "observation_date" if "observation_date" in df.columns else df.columns[0]
    )
    value_col = series_id if series_id in df.columns else df.columns[-1]
    dates = pd.to_datetime(df[date_col], errors="coerce", utc=True)
    values = pd.to_numeric(df[value_col], errors="coerce")
    s = pd.Series(values.to_numpy(), index=dates, name=series_id).dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()


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


def expected_positions(
    module_result: dict,
    close: pd.Series,
    ndx: pd.Series,
    usdjpy: pd.Series,
) -> pd.Series:
    expected = pd.Series(np.nan, index=close.index, dtype=float)
    for fold in module_result["folds"]:
        params = fold["selected_params"]
        if module_result["module"] == "volatility_regime":
            signal = volatility_regime_signal(close, params)
        elif module_result["module"] == "cross_market_confirmation":
            signal = cross_market_signal(close, ndx, usdjpy, params)
        else:
            raise ValueError(f"Unsupported second-engine module {module_result['module']}")
        position = signal.shift(1).fillna(0.0)
        mask = (close.index >= pd.Timestamp(fold["test_from"], tz="UTC")) & (
            close.index <= pd.Timestamp(fold["test_to"], tz="UTC")
        )
        expected.loc[mask] = position.loc[mask]
    return expected.dropna().astype(int)


def target_after_bar(expected: pd.Series, close_index: pd.DatetimeIndex) -> dict[str, int]:
    targets: dict[str, int] = {}
    loc = {ts: i for i, ts in enumerate(close_index)}
    for ts, value in expected.items():
        i = loc[ts]
        if i == 0:
            continue
        prev = close_index[i - 1]
        targets[prev.date().isoformat()] = int(value)
    return targets


def expected_fill_units(targets: dict[str, int], close: pd.Series) -> int:
    current = 0
    units = 0
    for ts in close.index:
        key = ts.date().isoformat()
        if key not in targets:
            continue
        desired = int(targets[key])
        units += abs(desired - current)
        current = desired
    return int(units)


class ReplayConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal


class ReplayTargetStrategy(Strategy):
    def __init__(
        self,
        config: ReplayConfig,
        targets: dict[str, int],
        expected_active: dict[str, int],
    ):
        super().__init__(config)
        self.targets = targets
        self.expected_active = expected_active
        self.audit_rows: list[dict] = []

    def on_start(self) -> None:
        self.subscribe_bars(self.config.bar_type)

    def _position_sign(self) -> int:
        if self.portfolio.is_net_long(self.config.instrument_id):
            return 1
        if self.portfolio.is_net_short(self.config.instrument_id):
            return -1
        return 0

    def _buy(self) -> None:
        instrument = self.cache.instrument(self.config.instrument_id)
        order = self.order_factory.market(
            self.config.instrument_id,
            OrderSide.BUY,
            instrument.make_qty(self.config.trade_size),
        )
        self.submit_order(order)

    def _sell(self) -> None:
        instrument = self.cache.instrument(self.config.instrument_id)
        order = self.order_factory.market(
            self.config.instrument_id,
            OrderSide.SELL,
            instrument.make_qty(self.config.trade_size),
        )
        self.submit_order(order)

    def on_bar(self, bar: Bar) -> None:
        ts = pd.Timestamp(int(bar.ts_event), unit="ns", tz="UTC")
        key = ts.date().isoformat()
        current = self._position_sign()

        if key in self.expected_active:
            expected = int(self.expected_active[key])
            self.audit_rows.append(
                {
                    "date": key,
                    "expected_position": expected,
                    "observed_position": current,
                    "match": bool(expected == current),
                }
            )

        if key not in self.targets:
            return

        desired = int(self.targets[key])
        if desired == current:
            return

        if current != 0:
            self.close_all_positions(self.config.instrument_id)

        if desired > 0:
            self._buy()
        elif desired < 0:
            self._sell()


def parse_commission(value: object) -> float:
    if value is None:
        return 0.0
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(match.group(0)) if match else 0.0


def run_engine(
    module_result: dict,
    close: pd.Series,
    ndx: pd.Series,
    usdjpy: pd.Series,
    fee_rate: Decimal,
    validation: dict,
) -> dict:
    expected = expected_positions(module_result, close, ndx, usdjpy)
    targets = target_after_bar(expected, close.index)
    expected_active = {ts.date().isoformat(): int(v) for ts, v in expected.items()}

    instrument_id = InstrumentId.from_str("JNU-PROXY.SIM")
    instrument = PerpetualContract(
        instrument_id=instrument_id,
        raw_symbol=Symbol("JNU-PROXY"),
        underlying="NIKKEI225",
        asset_class=AssetClass.INDEX,
        quote_currency=JPY,
        settlement_currency=JPY,
        is_inverse=False,
        price_precision=2,
        size_precision=0,
        price_increment=Price.from_str("0.01"),
        size_increment=Quantity.from_int(1),
        multiplier=Quantity.from_int(1),
        lot_size=Quantity.from_int(1),
        margin_init=Decimal("0.10"),
        margin_maint=Decimal("0.05"),
        maker_fee=fee_rate,
        taker_fee=fee_rate,
        ts_event=0,
        ts_init=0,
    )

    bars_df = pd.DataFrame(
        {
            "open": close.astype(float),
            "high": close.astype(float),
            "low": close.astype(float),
            "close": close.astype(float),
            "volume": 1.0,
        },
        index=close.index,
    )
    bar_type = BarType.from_str("JNU-PROXY.SIM-1-DAY-LAST-EXTERNAL")
    bars = BarDataWrangler(bar_type, instrument).process(bars_df)

    engine = BacktestEngine(
        BacktestEngineConfig(
            trader_id=TraderId("JNU-SECOND-ENGINE"),
            logging=LoggingConfig(log_level="ERROR"),
        )
    )
    sim = Venue("SIM")
    engine.add_venue(
        venue=sim,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=JPY,
        starting_balances=[Money(100_000_000, JPY)],
        default_leverage=Decimal(1),
    )
    engine.add_instrument(instrument)
    engine.add_data(bars)

    strategy = ReplayTargetStrategy(
        ReplayConfig(
            instrument_id=instrument_id,
            bar_type=bar_type,
            trade_size=Decimal("1"),
        ),
        targets=targets,
        expected_active=expected_active,
    )
    engine.add_strategy(strategy)
    engine.run()

    fills = engine.trader.generate_fills_report()
    orders = engine.trader.generate_orders_report()

    audit = pd.DataFrame(strategy.audit_rows)
    match_ratio = float(audit["match"].mean()) if len(audit) else 0.0
    actual_fills = int(len(fills))
    expected_units = expected_fill_units(targets, close)

    price_errors: list[float] = []
    commissions: list[float] = []
    if len(fills):
        for _, row in fills.iterrows():
            fill_ts = pd.Timestamp(row["ts_event"])
            if fill_ts.tzinfo is None:
                fill_ts = fill_ts.tz_localize("UTC")
            else:
                fill_ts = fill_ts.tz_convert("UTC")
            key = fill_ts.normalize()
            if key in close.index:
                price_errors.append(abs(float(row["last_px"]) - float(close.loc[key])))
            commissions.append(parse_commission(row.get("commission")))

    nonfilled = 0
    if len(orders) and "status" in orders.columns:
        nonfilled = int((orders["status"].astype(str) != "FILLED").sum())

    max_price_error = float(max(price_errors)) if price_errors else 0.0
    checks = {
        "position_match_ratio": match_ratio
        >= float(validation.get("min_position_match_ratio", 1.0)),
        "fill_count_match": (
            actual_fills == expected_units
            if bool(validation.get("require_fill_count_match", True))
            else True
        ),
        "fill_price_error": max_price_error
        <= float(validation.get("max_fill_price_abs_error", 1e-6)),
        "all_orders_filled": (
            nonfilled == 0
            if bool(validation.get("require_all_orders_filled", True))
            else True
        ),
    }

    result = engine.get_result()
    engine.dispose()

    return {
        "module": module_result["module"],
        "status": "PASS_ENGINE_REPLAY" if all(checks.values()) else "FAIL_ENGINE_REPLAY",
        "checks": checks,
        "position_audit": {
            "oos_days": int(len(audit)),
            "matches": int(audit["match"].sum()) if len(audit) else 0,
            "match_ratio": match_ratio,
        },
        "execution": {
            "expected_fill_units_from_target_changes": expected_units,
            "actual_fill_events": actual_fills,
            "order_count": int(len(orders)),
            "nonfilled_order_count": nonfilled,
            "max_fill_price_abs_error": max_price_error,
            "total_reported_commission_jpy": float(sum(commissions)),
            "fee_rate_per_fill_notional": float(fee_rate),
        },
        "nautilus_result": {
            "stats_returns": getattr(result, "stats_returns", None),
            "stats_pnls": getattr(result, "stats_pnls", None),
        },
        "first_engine_reference": {
            "oos_metrics": module_result["oos_metrics"],
            "status": module_result["status"],
        },
    }


def report_markdown(result: dict) -> str:
    lines = [
        f"# Nautilus second-engine validation: {result['request_id']}",
        "",
        f"- NautilusTrader: {result['engine']['nautilus_version']}",
        f"- Source suite: {result['source_suite_result']}",
        f"- Source hashes match: **{result['source_hash_match']}**",
        f"- Overall status: **{result['overall_status']}**",
        "",
        "## Modules",
        "",
        "| Module | Status | Position match | Fills expected/actual | Max fill px error | Commission JPY |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for m in result["modules"]:
        e = m["execution"]
        a = m["position_audit"]
        lines.append(
            f"| {m['module']} | {m['status']} | {a['match_ratio']:.1%} | "
            f"{e['expected_fill_units_from_target_changes']}/{e['actual_fill_events']} | "
            f"{e['max_fill_price_abs_error']:.6f} | "
            f"{e['total_reported_commission_jpy']:.2f} |"
        )
    lines += [
        "",
        "## Scope",
        "",
        "- This second engine does not re-select parameters.",
        "- It independently rebuilds the two causal signal formulas from the published walk-forward fold parameters.",
        "- It verifies Nautilus event sequencing, active OOS position state, market-fill count, current-bar fill price, and fee accounting.",
        "- Commission plus requested slippage is represented as an equivalent taker fee because daily close-only proxy bars cannot identify a real bid/ask slippage path.",
        "- PASS_ENGINE_REPLAY is not VALIDATED_JNU_MODULE. Purged/CPCV and multiple-testing/overfit diagnostics remain before promotion.",
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
    if request.get("request_id") != request_id:
        raise ValueError("request_id must match filename stem")

    suite_path = ROOT / request["source_suite_result"]
    suite = json.loads(suite_path.read_text(encoding="utf-8"))

    wanted = set(request["modules"])
    selected = [m for m in suite["modules"] if m["module"] in wanted]
    if set(m["module"] for m in selected) != wanted:
        raise ValueError("Requested module missing from source suite")

    if bool(request.get("require_first_engine_pass", True)):
        failed = [m["module"] for m in selected if not m.get("second_engine_eligible")]
        if failed:
            raise ValueError(f"Modules not eligible from first engine: {failed}")

    source_bytes: dict[str, bytes] = {}
    source_meta = suite["data"]["sources"]
    cache_hits = {}
    hash_checks = {}
    for key, cache_name in CACHE_NAMES.items():
        meta = source_meta[key]
        raw, cache_hit = get_bytes(meta["url"], cache_name, meta["sha256"])
        source_bytes[key] = raw
        cache_hits[key] = cache_hit
        hash_checks[key] = digest(raw) == meta["sha256"]

    source_hash_match = all(hash_checks.values())
    if (
        bool(request.get("validation", {}).get("require_source_hash_match", True))
        and not source_hash_match
    ):
        raise RuntimeError("Second engine could not reproduce first-engine source hashes")

    close = parse_nikkei(source_bytes["nikkei_futures"])
    close = close.loc[
        pd.Timestamp(suite["data"]["date_from"], tz="UTC"):
        pd.Timestamp(suite["data"]["date_to"], tz="UTC")
    ]
    ndx = parse_fred(source_bytes["nasdaq100_fred"], "NASDAQ100").reindex(close.index).ffill()
    usdjpy = parse_fred(source_bytes["usdjpy_fred"], "DEXJPUS").reindex(close.index).ffill()

    cp = request["cost_proxy"]
    fee_rate = Decimal(
        str((float(cp["commission_bps"]) + float(cp["slippage_bps"])) / 10_000.0)
    )

    module_results = [
        run_engine(
            m,
            close,
            ndx,
            usdjpy,
            fee_rate,
            request.get("validation", {}),
        )
        for m in selected
    ]

    import nautilus_trader

    overall = source_hash_match and all(
        m["status"] == "PASS_ENGINE_REPLAY" for m in module_results
    )
    result = {
        "request_id": request_id,
        "status": "complete",
        "overall_status": "PASS_SECOND_ENGINE" if overall else "FAIL_SECOND_ENGINE",
        "source_suite_result": request["source_suite_result"],
        "source_hash_match": source_hash_match,
        "source_hash_checks": hash_checks,
        "market_data_cache_hits": cache_hits,
        "engine": {
            "name": "NautilusTrader",
            "nautilus_version": getattr(nautilus_trader, "__version__", "unknown"),
            "python_version": sys.version.split()[0],
            "role": "independent event/order/fill replay, not parameter search",
        },
        "cost_proxy": {
            **cp,
            "effective_taker_fee_rate": float(fee_rate),
        },
        "modules": module_results,
        "promotion_status": "SECOND_ENGINE_CHECK_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    RESULTS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    out_json.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    out_md.write_text(report_markdown(result), encoding="utf-8")
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
