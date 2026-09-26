from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

MARKET_OSE_NUMERIC = 207
MAX_LEVELS = 10

def _f(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default

def _i(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default

@dataclass
class OrderBook:
    bids: Dict[int, tuple[float, int]] = field(default_factory=dict)
    asks: Dict[int, tuple[float, int]] = field(default_factory=dict)
    updated_monotonic: float = 0.0

    def set_side_block(self, side: str, start_level: int, prices: List[Any], sizes: List[Any]) -> None:
        target = self.bids if side == "bid" else self.asks
        for idx, (p, q) in enumerate(zip(prices, sizes), start=start_level):
            if idx > MAX_LEVELS:
                break
            price, size = _f(p), _i(q)
            if price > 0 and abs(price) < 900_000_000:
                target[idx] = (price, max(size, 0))
            else:
                target.pop(idx, None)
        self.updated_monotonic = time.monotonic()

    def _sum_size(self, side: Dict[int, tuple[float, int]], levels: int) -> int:
        return sum(side.get(i, (0.0, 0))[1] for i in range(1, levels + 1))

    def metrics(self) -> dict:
        bid = self.bids.get(1, (0.0, 0))
        ask = self.asks.get(1, (0.0, 0))
        spread = ask[0] - bid[0] if bid[0] and ask[0] else None
        mid = (ask[0] + bid[0]) / 2 if bid[0] and ask[0] else None
        denom = bid[1] + ask[1]
        microprice = ((ask[0] * bid[1]) + (bid[0] * ask[1])) / denom if denom and bid[0] and ask[0] else None

        def imbalance(levels: int) -> Optional[float]:
            b = self._sum_size(self.bids, levels)
            a = self._sum_size(self.asks, levels)
            d = b + a
            return (b - a) / d if d else None

        return {
            "best_bid": bid[0] or None,
            "best_bid_size": bid[1] or None,
            "best_ask": ask[0] or None,
            "best_ask_size": ask[1] or None,
            "spread": spread,
            "mid": mid,
            "microprice": microprice,
            "book_imbalance_l1": imbalance(1),
            "book_imbalance_l5": imbalance(5),
            "book_imbalance_l10": imbalance(10),
            "depth_levels_bid": len(self.bids),
            "depth_levels_ask": len(self.asks),
        }

@dataclass
class Trade:
    ts: str
    price: float
    size: int
    bid: float
    ask: float
    seq: int
    inout: int

@dataclass
class FlowWindow:
    maxlen: int = 5000
    trades: Deque[Trade] = field(default_factory=deque)

    def add(self, trade: Trade) -> None:
        if self.trades.maxlen != self.maxlen:
            self.trades = deque(self.trades, maxlen=self.maxlen)
        elif self.trades.maxlen is None:
            self.trades = deque(self.trades, maxlen=self.maxlen)
        self.trades.append(trade)

    def metrics(self) -> dict:
        buy = sum(t.size for t in self.trades if t.inout in (1, 3))
        sell = sum(t.size for t in self.trades if t.inout in (0, 2))
        total = buy + sell
        last = self.trades[-1] if self.trades else None
        return {
            "trades": len(self.trades),
            "aggressive_buy_volume": buy,
            "aggressive_sell_volume": sell,
            "trade_delta": buy - sell,
            "trade_imbalance": (buy - sell) / total if total else None,
            "last_trade_price": last.price if last else None,
            "last_trade_size": last.size if last else None,
            "last_trade_seq": last.seq if last else None,
            "last_trade_time": last.ts if last else None,
        }

class FeedState:
    def __init__(self, stock_code: str):
        self.stock_code = stock_code
        self.book = OrderBook()
        self.flow = FlowWindow()
        self.login_ok = False
        self.market_seen = None
        self.events = 0
        self.depth_events = 0
        self.trade_events = 0
        self.started = time.monotonic()

    def snapshot(self) -> dict:
        return {
            "source": "YUANTA_SPARK_API",
            "market_expected": "OSE",
            "stock_code": self.stock_code,
            "login_ok": self.login_ok,
            "market_seen": str(self.market_seen) if self.market_seen is not None else None,
            "events": self.events,
            "depth_events": self.depth_events,
            "trade_events": self.trade_events,
            "book": self.book.metrics(),
            "flow": self.flow.metrics(),
            "capture_age_seconds": round(time.monotonic() - self.started, 3),
            "trading_capability_exposed": False,
        }

def _block_values(obj: Any, prefix_price: str, prefix_vol: str, count: int = 5) -> tuple[list, list]:
    prices, sizes = [], []
    for i in range(1, count + 1):
        prices.append(getattr(obj, f"{prefix_price}{i}", 0))
        sizes.append(getattr(obj, f"{prefix_vol}{i}", 0))
    return prices, sizes

def apply_depth_event(state: FeedState, fresult: Any, enum_five: Any) -> None:
    state.events += 1
    state.depth_events += 1
    state.market_seen = getattr(fresult, "MarketType", state.market_seen)
    flag = getattr(fresult, "IndexFlag", None)

    if flag == enum_five.IndexFlag20:
        o = fresult.IndexFlag_20
        p, q = _block_values(o, "Price", "Vol")
        state.book.set_side_block("bid", 1, p, q)
    elif flag == enum_five.IndexFlag21:
        o = fresult.IndexFlag_21
        p, q = _block_values(o, "Price", "Vol")
        state.book.set_side_block("ask", 1, p, q)
    elif flag == enum_five.IndexFlag42:
        o = fresult.IndexFlag_42
        p, q = _block_values(o, "Price", "Vol")
        state.book.set_side_block("bid", 6, p, q)
    elif flag == enum_five.IndexFlag43:
        o = fresult.IndexFlag_43
        p, q = _block_values(o, "Price", "Vol")
        state.book.set_side_block("ask", 6, p, q)
    elif flag == enum_five.IndexFlag50:
        o = fresult.IndexFlag_50
        bp, bq = _block_values(o, "BuyPrice", "BuyVol")
        ap, aq = _block_values(o, "SellPrice", "SellVol")
        state.book.set_side_block("bid", 1, bp, bq)
        state.book.set_side_block("ask", 1, ap, aq)
    elif flag == enum_five.IndexFlag51:
        o = fresult.IndexFlag_51
        bp, bq = _block_values(o, "BuyPrice", "BuyVol")
        ap, aq = _block_values(o, "SellPrice", "SellVol")
        state.book.set_side_block("bid", 6, bp, bq)
        state.book.set_side_block("ask", 6, ap, aq)

def _yuanta_time_to_str(t: Any) -> str:
    if t is None:
        return ""
    parts = [
        getattr(t, "bytHour", None),
        getattr(t, "bytMin", None),
        getattr(t, "bytSec", None),
        getattr(t, "ushtMSec", None),
    ]
    if all(x is not None for x in parts):
        return f"{parts[0]:02d}:{parts[1]:02d}:{parts[2]:02d}.{parts[3]:03d}"
    return str(t)

def apply_trade_event(state: FeedState, result: Any) -> None:
    state.events += 1
    state.trade_events += 1
    state.market_seen = getattr(result, "MarketType", state.market_seen)
    serial = _i(getattr(result, "SerialNo", 0))
    if serial < 0:
        return
    state.flow.add(
        Trade(
            ts=_yuanta_time_to_str(getattr(result, "Time", None)),
            price=_f(getattr(result, "DealPrice", 0)),
            size=max(_i(getattr(result, "DealVol", 0)), 0),
            bid=_f(getattr(result, "BuyPrice", 0)),
            ask=_f(getattr(result, "SellPrice", 0)),
            seq=serial,
            inout=_i(getattr(result, "InOutFlag", -1), -1),
        )
    )

def _load_yuanta():
    api_dir = os.environ.get("YUANTA_SPARK_API_DIR")
    if not api_dir:
        raise RuntimeError("YUANTA_SPARK_API_DIR is required for live mode")
    api_path = Path(api_dir).expanduser().resolve()
    if not api_path.exists():
        raise RuntimeError(f"Yuanta API directory not found: {api_path}")

    sys.path.append(str(api_path))
    if sys.platform == "win32":
        os.add_dll_directory(str(api_path))

    from pythonnet import load
    load("coreclr")
    import clr
    clr.AddReference("System.Collections")
    clr.AddReference("YuantaSparkAPI")
    from System.Collections.Generic import List
    from YuantaOneAPI import (
        YuantaSparkAPITrader,
        enumLogType,
        enumMarketType,
        enumEnvironmentMode,
        enumQuoteFiveTickIndexType,
        FiveTickA,
        StockTick,
    )
    return {
        "List": List,
        "Trader": YuantaSparkAPITrader,
        "LogType": enumLogType,
        "MarketType": enumMarketType,
        "Env": enumEnvironmentMode,
        "FiveEnum": enumQuoteFiveTickIndexType,
        "FiveTickA": FiveTickA,
        "StockTick": StockTick,
    }

def run_live(stock_code: str, seconds: int, jsonl: Optional[str]) -> int:
    account = os.environ.get("YUANTA_ACCOUNT")
    password = os.environ.get("YUANTA_PASSWORD")
    if not account or not password:
        raise RuntimeError("YUANTA_ACCOUNT and YUANTA_PASSWORD are required for live mode")
    if not stock_code or stock_code.strip().upper() == "JNU":
        raise RuntimeError("Use the exact Yuanta individual-month StockCode, not bare JNU")

    y = _load_yuanta()
    state = FeedState(stock_code)
    trader = y["Trader"]()
    trader.SetLogType(y["LogType"].COMMON)

    def on_response(intMark, dwIndex, strIndex, objHandle, objValue):
        try:
            if intMark == 1 and strIndex == "Login":
                status = objValue.LoginStatus
                code = str(status.MsgCode)
                state.login_ok = code in {"0001", "00001"} or _i(status.Count) > 0
                return
            if intMark == 2 and strIndex == "SubscribeFiveTickA":
                apply_depth_event(state, objValue, y["FiveEnum"])
                return
            if intMark == 2 and strIndex == "SubscribeStockTick":
                apply_trade_event(state, objValue)
                return
        except Exception:
            # Never leak credentials through callback exceptions.
            return

    trader.OnResponse += on_response
    trader.Open(y["Env"].PROD)
    time.sleep(1.5)
    trader.Login(account, password)

    deadline = time.monotonic() + 8
    while time.monotonic() < deadline and not state.login_ok:
        time.sleep(0.1)
    if not state.login_ok:
        trader.Close()
        trader.Dispose()
        raise RuntimeError("Yuanta login did not confirm success; no market subscription started")

    five_list = y["List"][y["FiveTickA"]]()
    five = y["FiveTickA"]()
    five.MarketType = y["MarketType"].OSE
    five.StockCode = stock_code
    five_list.Add(five)

    tick_list = y["List"][y["StockTick"]]()
    tick = y["StockTick"]()
    tick.MarketType = y["MarketType"].OSE
    tick.StockCode = stock_code
    tick_list.Add(tick)

    trader.SubscribeFiveTickA(account, five_list)
    trader.SubscribeStockTick(account, tick_list)

    output = Path(jsonl).expanduser().resolve() if jsonl else None
    end = time.monotonic() + max(seconds, 1)
    last_emit = 0.0
    try:
        while time.monotonic() < end:
            now = time.monotonic()
            if now - last_emit >= 1.0:
                snap = state.snapshot()
                line = json.dumps(snap, ensure_ascii=False, separators=(",", ":"))
                print(line, flush=True)
                if output:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    with output.open("a", encoding="utf-8") as f:
                        f.write(line + "\n")
                last_emit = now
            time.sleep(0.05)
    finally:
        try:
            trader.UnSubscribeFiveTickA(account, five_list)
            trader.UnSubscribeStockTick(account, tick_list)
        except Exception:
            pass
        try:
            trader.LogOut()
        except Exception:
            pass
        trader.Close()
        trader.Dispose()

    snap = state.snapshot()
    if snap["trade_events"] == 0 and snap["depth_events"] == 0:
        return 3
    if snap["trade_events"] > 0 and snap["depth_events"] == 0:
        return 2
    return 0

class _Flag:
    def __init__(self, **kw):
        self.__dict__.update(kw)

class _Enums:
    IndexFlag20 = 20
    IndexFlag21 = 21
    IndexFlag42 = 42
    IndexFlag43 = 43
    IndexFlag50 = 50
    IndexFlag51 = 51

def selftest() -> int:
    s = FeedState("JNU_TEST")
    f50 = _Flag(
        MarketType="OSE", StkCode="JNU_TEST", IndexFlag=50,
        IndexFlag_50=_Flag(
            **{f"BuyPrice{i}": 66000 - (i-1)*5 for i in range(1,6)},
            **{f"BuyVol{i}": 10*i for i in range(1,6)},
            **{f"SellPrice{i}": 66005 + (i-1)*5 for i in range(1,6)},
            **{f"SellVol{i}": 12*i for i in range(1,6)},
        )
    )
    f51 = _Flag(
        MarketType="OSE", StkCode="JNU_TEST", IndexFlag=51,
        IndexFlag_51=_Flag(
            **{f"BuyPrice{i}": 65975 - (i-1)*5 for i in range(1,6)},
            **{f"BuyVol{i}": 8*i for i in range(1,6)},
            **{f"SellPrice{i}": 66030 + (i-1)*5 for i in range(1,6)},
            **{f"SellVol{i}": 9*i for i in range(1,6)},
        )
    )
    apply_depth_event(s, f50, _Enums)
    apply_depth_event(s, f51, _Enums)
    for n, flag in enumerate([1,1,0,1,0], start=1):
        apply_trade_event(s, _Flag(
            MarketType="OSE", SerialNo=n, Time=f"08:45:0{n}.000",
            DealPrice=66000 + n*5, DealVol=n, BuyPrice=66000, SellPrice=66005,
            InOutFlag=flag
        ))
    snap = s.snapshot()
    checks = {
        "ten_bid_levels": snap["book"]["depth_levels_bid"] == 10,
        "ten_ask_levels": snap["book"]["depth_levels_ask"] == 10,
        "spread_5": snap["book"]["spread"] == 5,
        "five_trades": snap["flow"]["trades"] == 5,
        "nonzero_delta": snap["flow"]["trade_delta"] != 0,
        "no_trading_capability": snap["trading_capability_exposed"] is False,
    }
    failed = [k for k,v in checks.items() if not v]
    print(json.dumps({"status":"PASS" if not failed else "FAIL","checks":checks,"snapshot":snap},ensure_ascii=False,indent=2))
    return 0 if not failed else 1

def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only JNU market-data adapter for Yuanta SPARK API")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    live = sub.add_parser("live-probe")
    live.add_argument("--stock-code", required=True)
    live.add_argument("--seconds", type=int, default=20)
    live.add_argument("--jsonl")
    args = ap.parse_args()
    if args.cmd == "selftest":
        return selftest()
    return run_live(args.stock_code, args.seconds, args.jsonl)

if __name__ == "__main__":
    raise SystemExit(main())
