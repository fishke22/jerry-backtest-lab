# JNU PCR directional candidate — durable framework memory — 2026-09-01

This note records only pre-outcome methodology and data-feasibility decisions. No post-2009 directional return outcome has been inspected.

## Governance
- Candidate is substantively independent and remains non-formal.
- Literature anchor: Tsuji (2009), Nikkei 225 index-options PCR.
- Original paper already contains threshold/rule selection risk; future validation must be strict post-publication replication.
- No threshold, horizon, venue, number-of-days, maturity, or indicator rescue after outcomes.

## Canonical information construction
- Monthly signal.
- Last five regular business days of the month.
- Near and second-near standard Nikkei 225 option maturities.
- Nearest OTM put: highest strike below same-day official Nikkei reference close.
- Nearest OTM call: lowest strike above same-day official Nikkei reference close.
- Daily PCR = 100 × two selected put volumes / two selected call volumes.
- Monthly PCR = arithmetic mean of five daily PCRs.
- Same official OSE/Osaka Exchange daily report supplies the reference Nikkei close and issue-level option fields.
- Modern national-holiday trading sessions are not extra business days for historical-convention replication.

## Data sources / rights boundary
- NDL Digital Collection daily reports for historical coverage.
- JPX current official daily-report archive for recent NDL-ingestion lag.
- 225Labo is used only for local trading-date calendar QA at this gate; no prices/returns.
- Raw NDL/JPX reports and 225Labo files are not mirrored to public GitHub.

## Coverage
2009-05 through 2026-08:
- 208 months.
- 205 months have 5/5 required regular-business-day reports (98.56%).
- 1,032 / 1,040 required reports available (99.23%).
- Non-full months: 2009-05 (3/5), 2009-06 (4/5), 2010-06 (0/5).
- From 2009-07 through 2026-08, only 2010-06 is missing.

## Current blocker
Cross-era schema is present in 2009, 2016 and 2024. Parser is not yet formally passed because some legacy auction rows split sparse numeric glyphs in the PDF text layer. A coordinate-based fallback must be validated on a frozen sample before data feasibility is promoted.

Current disposition: DATA_INCONCLUSIVE_PARSER_ROBUSTNESS_PENDING.
