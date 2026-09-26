---
name: jnu-yuanta-readonly-feed
description: Read exact Osaka Nikkei 225 Micro (JNU) quotes, order-book depth and trades from the user's authorized Yuanta SPARK API without any trading capability. Use for JNU Research when exact OSE individual-contract live data, order-flow, microprice or freshness validation is needed.
version: "1.1.0"
---

# JNU Yuanta Read-Only Feed

This skill is the preferred exact-market-data path for JNU Research. Exact OSE Micro live quote and current-day tick-detail retrieval are already evidenced on the user's authorized Yuanta SPARK setup. Five/ten-level depth and streaming StockTick remain unverified until a matching live-session probe succeeds.

## Safety boundary

- Read-only market data only.
- Never place, modify, cancel or stage an order.
- Never call trading/conditional-order methods.
- Never print or persist passwords, certificate passwords or personal identifiers.
- Credentials are supplied locally at runtime and are not stored in GitHub.
- The exact individual JNU contract month is mandatory. Never substitute a continuous contract.
- **Single-owner rule:** if an existing Yuanta quote owner is RUNNING/DEGRADED with `startup_stage=RUNNING`, do not create another broker login. Consume the existing hub read-only.

## Required JNU Research files

Read these first:

1. `config/jnu_operational_framework_cross_session_memory_v1.json`
2. `config/jnu_operational_framework_current_v1_9.json`
3. `config/jnu_cross_session_precision_analysis_memory_v1.json`
4. `config/jnu_yuanta_readonly_feed_v1.json`

## Source decision

1. Prefer the existing single-owner Yuanta SPARK quote hub when it is running; read its snapshot/Parquet/control outputs without another broker login.
2. If no owner exists and the operator explicitly allows a maintenance probe, use the authorized Yuanta SPARK API exact JNU contract.
3. Exact live quote and current-day tick-detail capability are already evidenced locally; L2/streaming-tick promotion is still gated on a matching live probe.
4. JPX public web futures prices are delayed by at least 15 minutes and are not acceptable as live order-flow evidence.
5. OSE real-time/full-order historical feeds are paid, except conditional free-trial programs. Do not label them permanently free.

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

For normal operation, prefer an already-running quote hub and do not require a second login. The existing hub directory can be supplied with `--hub-dir`.

Only for an explicitly authorized standalone maintenance probe, the installed Yuanta SPARK API directory must contain `YuantaSparkAPI.dll` and the vendor files required by Yuanta.

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

Read an existing single-owner hub without broker mutation:

```
python scripts/yuanta_jnu_readonly_feed.py hub-status --hub-dir "<YUANTA_HUB_DIR>"
```

Standalone L2/streaming-tick probe is **disabled by default**. Run it only during an active OSE session, only if no verified owner exists, and only after explicit maintenance approval:

```
python scripts/yuanta_jnu_readonly_feed.py live-probe --stock-code "<YUANTA_EXACT_JNU_STOCK_CODE>" --seconds 20 --allow-standalone-login
```

Optional standalone JSONL capture (same explicit-maintenance rules):

```
python scripts/yuanta_jnu_readonly_feed.py live-probe --stock-code "<YUANTA_EXACT_JNU_STOCK_CODE>" --seconds 60 --jsonl "jnu_feed.jsonl" --allow-standalone-login
```

## Promotion rule

Current promotion state:

- exact OSE Micro individual-contract live quote: **VERIFIED**;
- exact JNU current-day `GetStkTickDetail`: **VERIFIED DATA RETURN**, with timestamp-evidence governance still enforced;
- `SubscribeStockTick` streaming ticks: **UNVERIFIED ACCOUNT CALLBACK**;
- `SubscribeFiveTickA` five/ten-level depth: **UNVERIFIED ACCOUNT CALLBACK**.

Do not promote L2/order-flow to authoritative status until the exact-contract live callback and freshness gates pass. No order API may be invoked.

If depth remains unverified, use exact live quote/current-day ticks only and label L2-derived metrics `UNAVAILABLE`.
If a future exact-contract FiveTickA + StockTick probe passes, promote only those observed capabilities; do not infer historical L2 availability.
