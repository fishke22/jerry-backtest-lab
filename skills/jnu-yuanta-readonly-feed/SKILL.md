---
name: jnu-yuanta-readonly-feed
description: Read exact Osaka Nikkei 225 Micro (JNU) quotes, order-book depth and trades from the user's authorized Yuanta SPARK API without any trading capability. Use for JNU Research when exact OSE individual-contract live data, order-flow, microprice or freshness validation is needed.
version: "1.0.0"
---

# JNU Yuanta Read-Only Feed

This skill is the preferred exact-market-data path for JNU Research **only after the live entitlement probe passes**.

## Safety boundary

- Read-only market data only.
- Never place, modify, cancel or stage an order.
- Never call trading/conditional-order methods.
- Never print or persist passwords, certificate passwords or personal identifiers.
- Credentials are supplied locally at runtime and are not stored in GitHub.
- The exact individual JNU contract month is mandatory. Never substitute a continuous contract.

## Required JNU Research files

Read these first:

1. `config/jnu_operational_framework_cross_session_memory_v1.json`
2. `config/jnu_operational_framework_current_v1_9.json`
3. `config/jnu_cross_session_precision_analysis_memory_v1.json`
4. `config/jnu_yuanta_readonly_feed_v1.json`

## Source decision

1. Prefer an authorized Yuanta SPARK API OSE feed if the user's account returns the exact JNU contract.
2. JPX public web futures prices are delayed by at least 15 minutes and are not acceptable as live order-flow evidence.
3. OSE real-time/full-order historical feeds are paid, except conditional free-trial programs. Do not label them permanently free.

## Yuanta fields used

Yuanta SPARK API officially exposes:

- `enumMarketType.OSE`
- `SubscribeStockTick`: trade/time/bid/ask/volume/inside-outside flag
- `SubscribeFiveTickA`: depth flags for levels 1-5 and 6-10
- `GetStkTickDetail`: current-day tick detail with sequence number and aggressor-side flag

The adapter derives:

- spread / midpoint
- L1/L5/L10 book imbalance
- microprice
- aggressive buy/sell volume
- trade delta / trade imbalance
- data freshness

## Local setup

The user's installed Yuanta SPARK API directory must contain `YuantaSparkAPI.dll` and the vendor files required by Yuanta.

Set local environment variables only for the process/session:

- `YUANTA_SPARK_API_DIR`
- `YUANTA_ACCOUNT`
- `YUANTA_PASSWORD`

Do not commit these values.

The exact `StockCode` must come from Yuanta's bundled `FunctionList.xls` / stock-name mapping. Search that vendor file for broker product code `JNU` and select the active individual month. Do not guess the code format.

## Commands

Offline implementation selftest:

```
python scripts/yuanta_jnu_readonly_feed.py selftest
```

Live entitlement probe (read-only):

```
python scripts/yuanta_jnu_readonly_feed.py live-probe --stock-code "<YUANTA_EXACT_JNU_STOCK_CODE>" --seconds 20
```

Optional JSONL capture:

```
python scripts/yuanta_jnu_readonly_feed.py live-probe --stock-code "<YUANTA_EXACT_JNU_STOCK_CODE>" --seconds 60 --jsonl "jnu_feed.jsonl"
```

## Promotion rule

Do not promote this feed to JNU authoritative exact-data status until a live probe confirms:

- MarketType is OSE,
- the returned StockCode exactly matches the intended JNU individual month,
- trade ticks arrive,
- depth arrives,
- timestamps are fresh enough,
- no order API was invoked.

If depth is unavailable but ticks work, mark `EXACT_JNU_L1_TICKS_ONLY`.
If neither exact ticks nor depth works, mark `YUANTA_OSE_ENTITLEMENT_UNAVAILABLE`.
