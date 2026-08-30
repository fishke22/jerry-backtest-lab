# JNU Dynamic Price Discovery Cloud Pilot

Status: `PILOT_ONLY_INSUFFICIENT_VENUE_COVERAGE`.

## Purpose

Test the preregistered `DYNAMIC_PRICE_DISCOVERY` architecture in the cloud before any formal promotion test.

## Cloud-first rule

- Execution: GitHub Actions standard hosted runner.
- Raw downloads: `.cache/market-data` through GitHub Actions cache.
- Raw market files are not committed to Git.
- Each result records source URL, symbol identity, SHA-256, cache-hit state and timestamp coverage.
- Local files are not an authoritative DPD source.

## Fixed pilot inputs

Free public-web proxies only:

- `NIY=F`: CME Nikkei 225 Yen futures proxy.
- `NKD=F`: CME Nikkei 225 Dollar futures proxy.
- `ES=F`: E-mini S&P 500 futures.
- `NQ=F`: E-mini Nasdaq-100 futures.
- `^N225`: Nikkei 225 cash index.

Intervals are fixed before the run:
- 1 minute / 8 days.
- 5 minutes / 60 days.
- Lead/lag window: ±3 bars.
- Chronological split: first 70% of trading days train, final 30% test.

## What this pilot can test

- Whether current Nikkei/US relationships are mostly synchronous or show short lead-lag structure.
- Whether ES/NQ adds incremental next-bar OOS information to the CME Nikkei proxy in Japan versus US cash sessions.
- Whether the signal survives from 1-minute to 5-minute resolution.

## What this pilot cannot validate

It cannot validate OSE ↔ SGX ↔ CME venue leadership because approved OSE and SGX contract-specific intraday datasets are not yet available in the cloud lab.

The promotion gate is hard-coded to FAIL until:
- OSE contract-specific intraday data is present;
- SGX contract-specific intraday data is present;
- same-expiry contract identity is aligned;
- storage/licensing is approved;
- walk-forward, cost-aware EV, recent-regime and multiple-testing gates pass.

No positive pilot result may be promoted to `VALIDATED_JNU_MODULE`.
