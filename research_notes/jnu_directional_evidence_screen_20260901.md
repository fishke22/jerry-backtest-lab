# JNU directional evidence screen — 2026-09-01

## Governance checkpoint

This screen was performed after reading the current `config/jnu_research_priority_queue.json`, not only the 2026-08-31 memory snapshot. The current queue has one active formal family: `MACD_4223_POST_PUBLICATION_TRUE_JNU_G1`. Under the one-active-family rule, no second formal directional family may be opened until that family is resolved and persisted.

Decision engine remains `NO_VALIDATED_DIRECTIONAL_EDGE`.

## Search objective

Find substantively independent, direct Nikkei 225 futures / OSE directional evidence that is not a rescue of any terminal family and that could justify a future preregistration without parameter fishing.

## Sources screened

### Kang (2021) — MACD on Nikkei 225 futures
- DOI: `10.3390/jrfm14010037`
- Direct Nikkei 225 futures evidence.
- Already converted into the active preregistered family `MACD_4223_POST_PUBLICATION_TRUE_JNU_G1` using the externally fixed `(4,22,3)` tuple and a clean post-publication holdout.
- Disposition: `ACTIVE_FAMILY_ALREADY_PREREGISTERED`; do not open a second family.

### Kang (2022) — MACD parameter methodology on Nikkei 225 futures
- DOI: `10.5430/ijfr.v13n3p1`
- Direct Nikkei 225 futures corroboration through 2021.
- Used only to define the post-publication boundary for the active MACD G1; not separate evidence for another family.
- Disposition: `CORROBORATION_ONLY_FOR_ACTIVE_MACD_G1`.

### Li, Endo, Zuo & Kishimoto (2010) — order imbalance
- DOI: `10.1080/00036840902881819`
- Direct Osaka Stock Exchange Nikkei 225 futures evidence; conventional plus limit-order imbalance explain a very large share of intraday return variation.
- Requires signed trade/order-flow and/or limit-order-book information. Existing OHLCV must not be relabeled as imbalance.
- Disposition: `HIGH_QUALITY_DIRECT_EVIDENCE_BUT_DATA_BLOCKED`; retain existing `OSE_ORDER_IMBALANCE` blocker, no preregistration from OHLCV.

### Hiraki, Maberly & Takezawa (1995) — end-of-day futures information
- DOI: `10.1016/0378-4266(94)00064-A`
- Direct Osaka Nikkei futures evidence, sample September 1988–June 1991. Unexpected EOD futures returns were positively related to overnight spot returns and subsequent spot trading-period returns.
- The paper itself states that the EOD Osaka futures trading segment generating the information channel had been eliminated. Target outcome is primarily subsequent spot return, not current JNU return.
- Disposition: `DO_NOT_OPEN_CURRENT_JNU_FAMILY`; historical market-design mechanism is not sufficiently portable to present JNU without a new direct bridge.

### Carchano & Pardo (2011) — calendar anomalies in stock-index futures
- DOI: `10.2139/ssrn.1958587`
- Tests 188 calendar effects across S&P 500, DAX and Nikkei futures, 1991–2008, with bootstrap/Monte Carlo controls.
- The only statistically/economically significant and persistent effect reported is turn-of-the-month in S&P 500 futures, not Nikkei.
- Disposition: `NEGATIVE_NIKKEI_EVIDENCE`; do not open a Nikkei calendar family.

### Lim (1996) and later Nikkei basis/mispricing literature
- Lim DOI: `10.1080/096031096334006`
- Direct Nikkei spot/futures basis literature; later work also documents mispricing adjustment and price discovery.
- Existing JNU governance already classifies `FUTURES_CASH_BASIS_ALPHA` as `DO_NOT_OPEN_SEPARATE_FAMILY`, allowing basis only for DPD/fair-value sanity, roll diagnostics and execution context.
- Disposition: `GOVERNANCE_EXCLUDED_AS_SEPARATE_ALPHA_FAMILY`.

## Connector/tool limitations encountered

- Consensus monthly search quota was exhausted at the time of this screen.
- Elicit connector account did not include API access.
- Scite monthly MCP quota was exhausted.
- SciSpace academic search and independent public web / publisher / RePEc / SSRN sources were used to continue the evidence screen without paid upgrades.

No paid source was authorized or used.

## Result

`NO_ADDITIONAL_DIRECTIONAL_FAMILY_OPENED_ACTIVE_MACD_G1_ONLY`

Reason:
1. Current governance already has one active preregistered formal directional family.
2. The strongest additional direct OSE evidence (order imbalance) remains data-blocked.
3. Historical EOD-information evidence is tied to an eliminated trading-session mechanism and predicts spot outcomes.
4. Calendar-anomaly literature provides negative rather than supporting Nikkei evidence after broad multiple-testing control.
5. Basis/mispricing is already governance-screened against opening as a separate alpha family.

Do not use these screened papers to rescue any terminal family. Do not weaken the current MACD G1 gates.

## Next research action

Resolve the active `MACD_4223_POST_PUBLICATION_TRUE_JNU_G1` Stage A exactly as preregistered. If Stage A fails, close it terminally with no parameter/filter rescue. If it passes, exact-JNU Stage B is the next permitted directional test. Only after the active family is resolved may another independent family be considered.
