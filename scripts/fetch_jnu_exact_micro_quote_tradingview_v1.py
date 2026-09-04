from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TAIPEI = timezone(timedelta(hours=8))
SYMBOL_RE = re.compile(r"^NK225MC[A-Z][0-9]{4}$")
QUOTE_URL = "https://quotes.tradingview.com/quote_cache_http/snapshot"
FIELDS = [
    "current_session",
    "type",
    "update_mode",
    "update_mode_seconds",
    "original_name",
    "short_name",
    "pro_name",
    "description",
    "local_description",
    "exchange",
    "source_id",
    "currency_code",
    "root",
    "expiration",
    "contract-date",
    "symbol_status",
    "lp",
    "ch",
    "chp",
    "lp_time",
    "bid",
    "ask",
    "rtc",
    "rch",
    "rchp",
]


def snapshot(symbol: str) -> dict:
    url = QUOTE_URL + "?" + urllib.parse.urlencode({"fields": ",".join(FIELDS)})
    body = json.dumps([f"OSE:{symbol}"]).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Origin": "https://www.tradingview.com",
            "Referer": "https://www.tradingview.com/",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 JNU-exact-micro-quote-adapter/1.3",
            "Cookie": "sessionid=; sessionid_sign=",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode("utf-8", "replace")
        http_status = int(r.status)
        response_date = r.headers.get("Date")

    if http_status != 200:
        raise RuntimeError(f"TradingView quote-cache HTTP status {http_status}")

    x = json.loads(raw)
    if not isinstance(x, list) or len(x) != 1:
        raise RuntimeError("unexpected TradingView quote-cache response shape")

    item = x[0]
    if not isinstance(item, dict):
        raise RuntimeError("TradingView quote-cache item is not an object")
    if item.get("symbol") != f"OSE:{symbol}":
        raise RuntimeError(f"TradingView quote-cache symbol mismatch: {item.get('symbol')!r}")
    if item.get("s") != "ok":
        raise RuntimeError(f"TradingView quote-cache status is not ok: {item.get('s')!r}")

    data = item.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("TradingView quote-cache data object missing")

    return {
        "data": data,
        "http_status": http_status,
        "http_response_date": response_date,
    }


def validate_and_build(symbol: str, snap: dict, max_age_seconds: int) -> dict:
    z = snap["data"]
    required = [
        "lp",
        "lp_time",
        "update_mode",
        "original_name",
        "description",
        "exchange",
        "source_id",
        "type",
        "currency_code",
        "root",
    ]
    missing = [k for k in required if z.get(k) is None]
    if missing:
        raise RuntimeError(f"TradingView quote-cache fields missing: {missing}")

    if z["exchange"] != "OSE" or z["source_id"] != "OSE":
        raise RuntimeError("quote-cache source/exchange identity is not OSE")
    if z["type"] != "futures":
        raise RuntimeError("quote-cache instrument type is not futures")
    if z["currency_code"] != "JPY":
        raise RuntimeError("quote-cache currency is not JPY")
    if z["root"] != "NK225MC":
        raise RuntimeError(f"quote-cache root is not NK225MC: {z['root']!r}")
    if "micro" not in str(z["description"]).lower():
        raise RuntimeError("quote-cache description does not identify Nikkei 225 Micro futures")
    if not str(z["original_name"]).startswith("OSE_DLY:NK225MC"):
        raise RuntimeError("quote-cache original_name is not an OSE delayed Micro contract")

    update_mode = str(z["update_mode"])
    if not update_mode.startswith("delayed_streaming"):
        raise RuntimeError(f"unexpected TradingView update_mode: {update_mode!r}")

    declared_delay = z.get("update_mode_seconds")
    if declared_delay is None:
        m = re.search(r"(?:_|-)(\d+)$", update_mode)
        if m:
            declared_delay = int(m.group(1))
    if declared_delay is not None:
        declared_delay = int(declared_delay)

    source_utc = datetime.fromtimestamp(float(z["lp_time"]), timezone.utc)
    source_at = source_utc.astimezone(TAIPEI)
    now = datetime.now(TAIPEI)
    age = (now - source_at).total_seconds()
    fresh = 0 <= age <= max_age_seconds

    price = float(z["lp"])
    if price <= 0:
        raise RuntimeError("quote-cache price must be positive")

    return {
        "version": "1.3",
        "provider": "TradingView anonymous OSE quote-cache snapshot",
        "data_provider_id": "tradingview_quote_cache_http",
        "source_id": z["source_id"],
        "source_original_name": z["original_name"],
        "symbol": symbol,
        "tradingview_symbol": f"OSE:{symbol}",
        "contract_name": z.get("description"),
        "contract_date": z.get("contract-date"),
        "expiration_epoch": z.get("expiration"),
        "exchange": "Osaka Exchange",
        "product": "Nikkei 225 micro Futures",
        "price": price,
        "displayed_price_same_atomic_snapshot": None,
        "dom_quote_price_equal": None,
        "bid": z.get("bid"),
        "ask": z.get("ask"),
        "currency": "JPY",
        "change": float(z["ch"]) if z.get("ch") is not None else None,
        "change_pct": float(z["chp"]) if z.get("chp") is not None else None,
        "market_state": z.get("current_session"),
        "source_timestamp_epoch": int(float(z["lp_time"])),
        "source_timestamp": source_at.isoformat(),
        "freshness_checked_at": now.isoformat(),
        "freshness_age_seconds": age,
        "maximum_allowed_age_seconds": max_age_seconds,
        "freshness_pass": fresh,
        "exact_product": True,
        "continuous_contract": False,
        "update_mode": update_mode,
        "declared_update_mode_seconds": declared_delay,
        "rt_update_period": None,
        "subsession_id": z.get("current_session"),
        "url": f"https://www.tradingview.com/symbols/OSE-{symbol}/",
        "quote_cache_endpoint": QUOTE_URL,
        "quote_cache_http_response_date": snap.get("http_response_date"),
        "delayed_data": True,
        "adapter_mode": "anonymous_quote_cache_http",
    }


def fetch_once(symbol: str, max_age_seconds: int) -> dict:
    return validate_and_build(symbol, snapshot(symbol), max_age_seconds)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    # Kept for CLI compatibility with the prior browser transport.
    ap.add_argument("--session", default="jnu_exact_micro")
    ap.add_argument("--reuse-session", action="store_true")
    ap.add_argument("--max-age-seconds", type=int, default=900)
    ap.add_argument("--max-wait-seconds", type=int, default=0)
    ap.add_argument("--poll-seconds", type=int, default=5)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    symbol = args.symbol.upper()
    if not SYMBOL_RE.fullmatch(symbol):
        raise RuntimeError(
            "symbol must be an individual OSE Nikkei 225 Micro contract such as NK225MCU2026"
        )
    if args.max_age_seconds <= 0:
        raise RuntimeError("max-age-seconds must be positive")

    deadline = time.monotonic() + max(0, args.max_wait_seconds)
    last: dict | None = None

    while True:
        last = fetch_once(symbol, args.max_age_seconds)
        if last["freshness_pass"]:
            break
        if args.max_wait_seconds <= 0 or time.monotonic() >= deadline:
            raise RuntimeError(
                "quote stale: "
                f"age={last['freshness_age_seconds']:.1f}s > {args.max_age_seconds}s; "
                f"source={last['source_timestamp']}"
            )
        time.sleep(max(1, args.poll_seconds))

    s = json.dumps(last, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(s + "\n", encoding="utf-8")
    print(s)


if __name__ == "__main__":
    main()
