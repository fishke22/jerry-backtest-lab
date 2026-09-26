---
name: jnu-yuanta-readonly-feed
description: Consume exact JNU market data from the user's existing MARKET_AI_HUB Yuanta single-owner recorder/runtime without creating a second broker login. Use when exact OSE individual-contract ticks, depth or freshness validation are needed.
version: "1.1.0"
---

# JNU Yuanta Read-Only Feed

This skill does **not** own broker authentication.

The authoritative local Yuanta implementation already exists under `D:\MARKET_AI_HUB` and must be reused.

## Safety boundary

- Read-only market data only.
- Never place, modify, cancel or stage an order.
- Never create a second Yuanta session just for JNU Research.
- Never ask the user to transmit broker passwords through ChatGPT.
- Credentials remain in MARKET_AI_HUB's Windows Credential Manager path.
- Exact individual JNU contract month is mandatory; continuous substitutes are prohibited.

## Required files

1. `config/jnu_operational_framework_cross_session_memory_v1.json`
2. `config/jnu_data_source_fallback_v1.json`
3. `config/jnu_yuanta_readonly_feed_v1.json`
4. `config/jnu_research_analysis_output_protocol_v1.json`

## Existing local owner

Reuse:

- `D:\MARKET_AI_HUB\src\market_ai_hub\integrations\yuanta\spark_runtime.py`
- `D:\MARKET_AI_HUB\src\market_ai_hub\integrations\yuanta\live_quote_recorder.py`
- `D:\MARKET_AI_HUB\data\live\yuanta\latest.json`
- `D:\MARKET_AI_HUB\data\live\yuanta\status.json`
- MARKET_AI_HUB MCP tools when the local host is reachable.

The local implementation already has:
- runtime-reflected OSE market number 207;
- exact `JNU\d{4}` contract validation;
- Windows Credential Manager integration;
- single-owner/fail-closed recorder controls;
- typed `GetStkTickDetail` request/callback tracing;
- one authorized real JNU2612 tick-detail capture from 2026-09-25.

That real batch proves exact-contract tick-detail retrieval can work. It does **not** prove continuous realtime depth. L2 remains unavailable until a real depth callback is observed.

## Data classification

- Fresh exact ticks + fresh depth -> `A_LOCAL_EXACT_FULL`
- Fresh exact ticks, no verified depth -> `B_LOCAL_EXACT_TICK_ONLY`
- Local unavailable, user supplies current broker quote/screenshot -> `C_MOBILE_MANUAL_EXACT_ANCHOR`
- Local unavailable, no exact user quote -> `D_MOBILE_CLOUD_PROXY_ONLY`
- Critical evidence unusable -> `E_INSUFFICIENT_DATA_ABSTAIN`

Never infer microprice/book imbalance from L1, delayed quotes or OHLC.

## Mobile rule

A mobile JNU request must not fail merely because `D:\MARKET_AI_HUB` is unreachable.

Automatically follow `config/jnu_data_source_fallback_v1.json` and provide the best safe analysis from connected cloud tools and official web sources. A user-supplied exact JNU price or screenshot is optional enrichment, not a prerequisite to answering.
