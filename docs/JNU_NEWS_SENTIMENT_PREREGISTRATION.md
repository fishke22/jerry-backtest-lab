# JNU News / Sentiment State Pre-registration

Updated: 2026-08-30

## Research question

Does a free, category-aware, causally time-aligned news state add out-of-sample information about next Japanese/Nikkei futures volatility before any attempt is made to trade sentiment directionally?

## Evidence basis

Direct Japanese research indicates that:
- news effects depend on category and subperiod;
- macro/public news and sentiment can shift Japanese return-volatility states;
- category-aware news features can outperform undifferentiated news indices;
- Japanese and English news can have different effects for Nikkei-related futures.

Therefore a single scalar "market sentiment" vote is prohibited.

## Free source selected for first proxy test

**GDELT DOC 2.0 TimelineTone + TimelineVol**

Reasons:
- no paid subscription;
- broad multilingual global-news monitoring;
- daily/hourly/15-minute timeline aggregation;
- normalized coverage volume and average tone;
- suitable for a low-cost state-screening test.

Limitations:
- GDELT tone is not MarketPsych/RavenPack and not equivalent to the sentiment measures in the cited papers;
- current historical indexing/reprocessing may differ from information that was observable in the exact historical production system;
- it is a proxy screen, not final validation.

## Pre-registered categories

1. JAPAN_BOJ_MACRO
   - Bank of Japan / BOJ / Japanese monetary policy / Japanese inflation
2. US_FED_MACRO
   - Federal Reserve / FOMC / US inflation / US payrolls
3. JPY_FX
   - Japanese yen / USDJPY / yen depreciation / yen appreciation
4. US_TECH_SEMICONDUCTOR
   - Nasdaq / semiconductor / Nvidia / chip
5. JAPAN_EQUITY_NIKKEI
   - Nikkei 225 / Japanese stocks / Tokyo stock market
6. GEOPOLITICAL_RISK
   - geopolitical risk / war / sanctions / tariff

These categories are fixed before seeing the results.

## Features

For each category:
- prior-day average tone;
- prior-day normalized coverage volume;
- prior-day absolute tone (emotion/intensity proxy);
- 3-day exponentially weighted tone, fixed half-life 2 days.

No feature selection after seeing results.

## Timing

A Japanese trading day may only use GDELT observations completed before that trading day. Same-day UTC news is not allowed to predict an already-open/closed Japanese session.

## Stage-1 target

Next-day squared Nikkei Futures Index return / volatility state.

Baseline:
- lagged daily squared return;
- 5-day average squared return;
- 22-day average squared return.

Forecast specification is fixed **before the first news run**:
- expanding OLS on log(next-day variance + epsilon);
- baseline predictors are log(lagged variance aggregates + epsilon);
- each category model adds all four pre-registered news features together;
- predicted log variance is exponentiated back to variance;
- no category-specific feature selection.

Each news category is added separately to the same baseline.

## Gate

A category is eligible for further research only if:
- OOS QLIKE improves vs baseline;
- OOS MSE improves vs baseline;
- block-bootstrap probability of positive QLIKE improvement >= 0.95;
- recent-window improvement is not negative;
- Holm correction across the six categories passes at alpha 0.10.

A pass means **NEWS_STATE_CANDIDATE**, not a directional trading signal.

## Explicit anti-overfit rule

Do not rewrite queries, categories, half-lives, thresholds, or category count after seeing this run merely to rescue a failure. Any changed specification becomes a new pre-registered research generation and must include the prior failed family in multiple-testing accounting.
