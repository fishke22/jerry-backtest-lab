---
name: jnu-data-source-fallback
description: Select the safest available JNU market-data mode across local Yuanta/MARKET_AI_HUB, mobile manual price anchoring, and cloud-only public/plugin sources. Use before every current or forward-looking JNU analysis.
version: "1.0.0"
---

# JNU Data Source Fallback

Always select a data mode before analyzing current/future JNU.

## Read first

1. `config/jnu_operational_framework_cross_session_memory_v1.json`
2. `config/jnu_data_source_fallback_v1.json`
3. `config/jnu_yuanta_readonly_feed_v1.json`
4. `config/jnu_research_analysis_output_protocol_v1.json`

## Mode selection

Use the first eligible mode:

- **A_LOCAL_EXACT_FULL** — exact JNU + fresh depth from MARKET_AI_HUB/Yuanta.
- **B_LOCAL_EXACT_TICK_ONLY** — exact JNU trade/tick data but no verified L2.
- **C_MOBILE_MANUAL_EXACT_ANCHOR** — local unavailable; user supplies current JNU quote/screenshot.
- **D_MOBILE_CLOUD_PROXY_ONLY** — no local and no exact current quote; use cloud plugins/official web with explicit proxy labels.
- **E_INSUFFICIENT_DATA_ABSTAIN** — critical evidence too stale/contradictory.

Never block a mobile answer just because the local PC is unavailable.

## Local exact path

Do **not** implement a second broker login.

Reuse `D:\MARKET_AI_HUB`:

- `src/market_ai_hub/integrations/yuanta/spark_runtime.py`
- `src/market_ai_hub/integrations/yuanta/live_quote_recorder.py`
- `data/live/yuanta/latest.json`
- `data/live/yuanta/status.json`
- local MARKET_AI_HUB MCP tools when the host is reachable.

Credentials remain in the existing Windows Credential Manager path. Never request or transmit them through ChatGPT.

The local bridge has already captured one authorized real `GetStkTickDetail` batch for exact `JNU2612`; this proves the bounded query path can return real exact-contract data. It does **not** prove continuous depth entitlement. Treat L2 as unavailable until a real depth callback is observed.

## Mobile/cloud path

When local is unavailable, use connected cloud tools as available:

- Jerry Market Research — J-Quants / EODHD and Japan/Taiwan structured data
- The Fly Market Intelligence — economic calendar and current market news
- Twelve Data — USDJPY, QQQ/SMH and cross-market prices
- Alpha Vantage — Treasury yields / macro / commodities
- Unusual Whales — US options/put-call context
- Longbridge / Fahali — supplemental US/Asia market state where relevant
- official web — JPX, Nikkei Indexes, BOJ, MOF

For exact Micro:
- use an approved individual-contract cloud observation only if its own timestamp passes the existing freshness gate;
- otherwise JPX delayed Micro is reference-only;
- never infer L2/order flow from delayed OHLC/last price.

## Manual exact anchor on mobile

If the user gives a current JNU last price or broker screenshot, use it only as:
- current exact price anchor,
- session/location anchor,
- level translation input.

Do not infer depth, queue, aggressor flow, or microprice from a screenshot unless those fields are visibly present and current.

## Output requirement

Every JNU answer must state:

`DATA MODE: <A/B/C/D/E>`

and briefly list:
- exact JNU source status,
- L2/order-flow status,
- critical unavailable fields,
- confidence cap caused by the mode.

