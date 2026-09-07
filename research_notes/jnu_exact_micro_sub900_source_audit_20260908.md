# JNU Exact-Micro Sub-900 Source Feasibility Audit — 2026-09-08

## Result

**FREE_PUBLIC_EXACT_MICRO_SUB900_SOURCE_NOT_FOUND**

The first-real governance chain remains technically ready, but the source gate is not operationally satisfiable with the free public exact-Micro transports currently verified.

The frozen maximum provider-timestamp age remains **900 seconds**. It is not relaxed.

## Scheduled evidence from 2026-09-07

Two real scheduled GitHub source-readiness runs completed successfully as workflows but produced **zero fresh sources**.

### Day-session scheduled run

- Run: `34072676355`
- Symbol: `NK225MCU2026`
- Status: `WAITING_FOR_FRESH_EXACT_MICRO`
- JPX A: 909.1 seconds old; margin to the 900-second gate = **-9.1 seconds**
- TradingView B: 909.8 seconds old; margin = **-9.8 seconds**

### Night-session scheduled run

- Run: `34131621161`
- Symbol: `NK225MCU2026`
- Status: `WAITING_FOR_FRESH_EXACT_MICRO`
- JPX A: 959.6 seconds old; margin = **-59.6 seconds**
- TradingView B: 960.0 seconds old; margin = **-60.0 seconds**

A green GitHub workflow therefore means only that the diagnostic executed correctly. It does **not** mean `FRESH_SOURCE_AVAILABLE`.

## Public-source audit

### JPX public futures prices

JPX states that futures prices on its public site are delayed by **at least 15 minutes**.

Evidence:
https://www.jpx.co.jp/english/quick-disclaimer/

This source has exact exchange/product identity but no positive operating margin inside a strict <=900-second gate.

### TradingView free OSE futures data

TradingView lists free Osaka Exchange futures data as **15-minute delayed**. Real-time OSE data is a paid market-data subscription.

Evidence:
https://www.tradingview.com/data-coverage/

The free tier therefore has no designed positive margin under a 900-second provider-timestamp gate.

### Tiger Brokers public futures pages

Tiger exposes exact individual OSE Micro contracts, including contract identity, but the public transport observed by this project is delayed mode. No stable free public sub-900 transport has been demonstrated.

Evidence:
https://www.itiger.com/futures/NK225MC2609

### Moomoo

Public Japan futures examples show **20-minute delayed** quotes, and Moomoo OpenAPI documentation currently lists Japanese-market futures as unsupported.

Evidence:
https://www.moomoo.com/stock/NK225M2712-JP/related-futures
https://openapi.moomoo.com/moomoo-api-doc/en/intro/authority.html

### Rakuten iSPEED

Public/widget documentation shows delayed display, while real-time access is tied to authenticated service. Broker authentication is outside the frozen JNU first-real governance.

Evidence:
https://www.rakuten-sec.co.jp/smartphone/ispeed/help/android/widget.html

### NikkeiRealtime

Prior protocol work demonstrated a real-time Micro continuous instrument but no admissible individual-month Micro identifier. Continuous-to-individual substitution remains terminally rejected.

## Governance consequence

The source-readiness workflow is now interpreted as **DETECTOR_ONLY_NOT_FIRST_REAL_GUARANTEE**.

First-real registration remains prohibited until a materially new source satisfies all of:

1. exact individual OSE Nikkei 225 Micro month contract;
2. provider timestamp age **<900 seconds with positive operational margin**;
3. stable cloud-fetchable transport;
4. public/no broker login/no trading permission;
5. source/provider timestamp preserved in provenance.

No quote-freshness, directional, confidence, horizon, scoring, or 30-nonabstain review rule is changed.

Formal state remains:

- `VALIDATED_JNU_MODULE = 0`
- `validated_directional_modules = 0`
- `decision_engine = NO_VALIDATED_DIRECTIONAL_EDGE`
- real forecasts = 0
- real outcomes = 0
