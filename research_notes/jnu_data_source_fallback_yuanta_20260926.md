# JNU Data Source Fallback / Yuanta Integration Findings — 2026-09-26

Status: **IMPLEMENTED / MOBILE FALLBACK MANDATORY / LOCAL EXACT SOURCE CONDITIONAL**

## Local finding

The user's existing `D:\MARKET_AI_HUB` already contains the authoritative local Yuanta integration and is more mature than a separate JNU Research broker client.

Relevant components:

- `src/market_ai_hub/integrations/yuanta/spark_runtime.py`
- `src/market_ai_hub/integrations/yuanta/live_quote_recorder.py`
- `src/market_ai_hub/integrations/yuanta/credential_store.py`
- `docs/architecture/v2-tick-detail-source-contract.md`
- `data/live/yuanta/latest.json`
- `data/live/yuanta/status.json`

Observed local evidence as of 2026-09-26:

- OSE market number = 207.
- Exact JNU contract syntax is validated as `JNU\d{4}`; `JNU2612` is an observed exact contract example.
- SPARK securities login has been accepted with MsgCode `0001`.
- Exact OSE Micro live quote delivery is verified: `JNUPM2612` (market 207) produced 8 exact-match `SubscribeWatchlistAll` callbacks on 2026-09-24.
- One authorized real exact-contract `GetStkTickDetail` batch for JNU2612 was captured on 2026-09-25.
- `SubscribeFiveTickA` L2/depth and `SubscribeStockTick` streaming ticks are not considered available until their own exact-contract live callbacks are observed.
- Trading/order capability remains prohibited.

Therefore JNU Research must reuse MARKET_AI_HUB's single-owner Yuanta lifecycle and must not create a second broker login.

## Public/free-data finding

No permanent free, legal source was found that provides both:

- exact individual-month OSE Nikkei 225 Micro real-time prices, and
- live L2/full-order-book data suitable for order-flow/microprice research.

Public JPX futures pages are delayed and are reference-only for live analysis. OSE/JPX historical tick/full-order products are paid; trial access may exist under specific conditions but is not permanent free data.

## Mandatory degradation ladder

JNU Research now selects the highest available mode:

1. `A_LOCAL_EXACT_FULL` — exact JNU + fresh depth from MARKET_AI_HUB/Yuanta.
2. `B_LOCAL_EXACT_TICK_ONLY` — exact JNU ticks but no verified L2.
3. `C_MOBILE_MANUAL_EXACT_ANCHOR` — local unavailable; user supplies current broker quote/screenshot.
4. `D_MOBILE_CLOUD_PROXY_ONLY` — no local and no exact current quote; use connected cloud tools and official sources.
5. `E_INSUFFICIENT_DATA_ABSTAIN` — critical evidence cannot be refreshed safely.

## Mobile cloud stack

When local access is unavailable, current connected tools can provide:

- Jerry Market Research — J-Quants / EODHD / FinMind structured data
- The Fly Market Intelligence — economic calendar and market news
- Twelve Data — USDJPY / QQQ / SMH and other cross-market prices
- Alpha Vantage — Treasury yields / macro / commodities
- Unusual Whales — U.S. options put/call context
- Longbridge / Fahali — supplemental market-state context
- Web/official sources — JPX, Nikkei Indexes, BOJ, MOF

These sources do not substitute for live OSE L2. They support regime, event, cross-market and path analysis only.

## Mobile operation rule

A current/future JNU request must never fail merely because the local computer is unavailable.

The analysis must:

- automatically degrade to the best cloud/mobile mode;
- explicitly state the selected DATA MODE;
- state whether exact JNU and L2/order-flow are available;
- cap confidence according to the mode;
- avoid false precision when exact live JNU price is unavailable.

A user-supplied current JNU quote or screenshot is optional and can re-anchor cloud analysis to an exact last price, but it does not create L2/order-flow evidence.
