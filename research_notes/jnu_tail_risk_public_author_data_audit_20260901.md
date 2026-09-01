# Tail-risk public author data audit — 2026-09-01

## Discovery
Lai Xu's public publications page links a Google Sheet labeled Data for Bollerslev, Todorov & Xu (2015), Tail Risk Premia and Return Predictability.

The public workbook was downloaded only to the local temporary research workspace for schema/provenance audit. It is not committed to this public repository because the page provides public access but does not explicitly state redistribution rights.

## Local audit
- Sheet: LJV
- Rows: 1,075
- Columns: 2
- Coverage: 1996-01-05 through 2017-05-19
- Local SHA-256: f787dd575ed697044866e34164c0c55b4f48c6f4c9d8eaec4bb765df2c0a6157
- 1996 through Aug-2013 subsample: mean(LJV)*100 = 0.4547; stdev(LJV)*100 = 0.5449.
- These closely reproduce the 2015 paper's published LJV mean 0.45 and stdev 0.54, strongly supporting series identity.

## What this unlocks
This substantially improves historical replication feasibility: the old derived U.S. LJV series is publicly supplied by an author, so historical LJV does not need to be reconstructed from paid OptionMetrics raw quotes for that interval.

## What it does not unlock
It does not create a valid new JNU directional family:
1. The public series stops in May 2017, before the 2021 Japanese predictability paper was published.
2. A genuine post-publication OOS test therefore still lacks predictor observations.
3. The Japanese paper characterizes yen-denominated Nikkei predictability as moderate/less compelling; significance is concentrated around 5-8 month horizons, while dollar-denominated results are much stronger.
4. This is a long-horizon risk-premium predictor, not direct evidence for nightly/intraday JNU direction.
5. Public access is not explicit permission to redistribute the raw author sheet, so the raw workbook remains local-only.

Disposition: PUBLIC_AUTHOR_LJV_HISTORY_FOUND_REPLICATION_ONLY_POSTPUBLICATION_OOS_STILL_BLOCKED. No formal directional family opened.

## Continuation search after Stage-5 BOJ closure
- Andersen/Todorov/Ubukata Japanese-equity sample runs through 2018-06, but no verified public post-publication continuation is supplied.
- Jacobs/Ke/Pan 2026 computes Bollerslev-style LJV/RJV over 1996-2021 and provides supplementary material, showing method continuation, but no reusable raw LJV series was verified.
- JPX June-2024 report extends Japanese option-implied LJV illustration through 2024-03; this is not U.S. LJV and cannot substitute for the candidate predictor.
- Suh/Yoo/Yoon 2021 states supporting data are available from the corresponding author on reasonable request; no self-service equivalent series was verified.
- Disposition remains: historical replication feasible, genuine post-2021 U.S.-LJV OOS data blocked; no formal directional family opened.
