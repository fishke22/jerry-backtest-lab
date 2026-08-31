# JNU directional evidence update — 2026-08-31

Status: literature/data-feasibility QA only. This document does **not** open a second formal family while NEWS_STATE_LANGUAGE_SOURCE_G1 is active.

## Direct Nikkei-futures evidence

Yasuhiro Iwanaga (2026), *How the prior day's S&P 500 returns influence the intraday returns of Nikkei 225 futures*, Finance Research Open 2(2), 100108, DOI: 10.1016/j.finr.2026.100108.

Public abstract/highlights report a state-dependent intraday pattern: a higher prior-day S&P 500 return is associated with lower Nikkei 225 futures returns in the first 30 minutes and higher returns in the last 30 minutes. The paper reports significant positive returns for reversal/momentum implementations, while noting that the proposed mechanisms are interpretations rather than directly tested causes.

Research implication already frozen in `config/jnu_intraday_path_us_g1_prereg.json`: do not use one universal U.S.-equity directional weight; test fixed FIRST_30M and LAST_30M interactions, with no post-result window optimization or NQ substitution.

## Supporting / cautionary evidence

Hiraki, Maberly & Takezawa (1995), *The information content of end-of-the-day index futures returns: International evidence from the Osaka Nikkei 225 futures contract*, Journal of Banking & Finance 19(5), DOI: 10.1016/0378-4266(94)00064-A, reports that unexpected end-of-day Osaka Nikkei futures returns are positively related to overnight spot returns and subsequent trading-period spot returns in their historical sample.

Li, Endo, Zuo & Kishimoto (2010), *Order imbalances explain 90% of returns of Nikkei 225 futures*, Applied Economics Letters 17(13), DOI: 10.1080/00036840902881819, gives direct OSE microstructure evidence but requires true signed/order-side information; OHLC/aggregate volume must not be used as a fake order-imbalance proxy.

## Data feasibility

JPX confirms Nikkei 225 mini opened on 2006-07-18 and currently trades 08:45–15:45 and 17:00–06:00 JST. Formal promotion of the intraday directional family remains blocked on approved true OSE minute data. Public-web review did not verify a free official long-history OSE minute-bar archive; do not treat this as proof that none exists.

225Labo or other personally licensed OSE raw minute data, if used, stays local-only. Cloud/GitHub may receive only non-reconstructable derived features, hashes, provenance, manifests and results consistent with the existing data-governance policy.

## Next action after active G1 disposition

1. If approved local OSE minute data becomes available, validate schema/timezone/session/contract-roll provenance locally.
2. Run the already-frozen `INTRADAY_PATH_US_TO_JNU_G1` family only after the active G1 family is terminal and persisted.
3. Keep H1 prior-US→FIRST_30M expected sign negative; H2 prior-US→LAST_30M expected sign positive; H3 compares universal-sign vs state interaction.
4. Use strict walk-forward OOS, block bootstrap, recent-regime stability and full JNU transaction-cost gate before any promotion.
5. If true OSE data remains unavailable, retain status DATA_BLOCKED; proxy sanity checks cannot become validated JNU alpha.
