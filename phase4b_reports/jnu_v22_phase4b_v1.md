# JNU Phase4B Evidence: jnu_v22_phase4b_v1

## USDJPY 1-day incremental state
- OOS days: 642
- MSE improvement: 2.89781e-06
- Bootstrap P(improvement > 0): 74.5%
- Sign accuracy: 54.7% -> 54.0%
- State gate: **FAIL**

## News / sentiment state

| Category | QLIKE Δ | MSE Δ | Bootstrap P+ | Recent QLIKE Δ | Holm | Status |
|---|---:|---:|---:|---:|---|---|
| JAPAN_BOJ_MACRO | 0.0241595 | 3.07263e-09 | 47.6% | -0.244036 | FAIL | FAIL_NEWS_STATE |
| US_FED_MACRO | 0.00541775 | 1.54494e-08 | 52.9% | -4.05487 | FAIL | FAIL_NEWS_STATE |
| JPY_FX | 0.589584 | 1.04792e-08 | 96.8% | 1.10394 | FAIL | FAIL_NEWS_STATE |
| US_TECH_SEMICONDUCTOR | 0.152108 | 3.69691e-08 | 72.0% | -0.327599 | FAIL | FAIL_NEWS_STATE |
| JAPAN_EQUITY_NIKKEI | -3.09107 | 5.81155e-09 | 28.5% | 0.424196 | FAIL | FAIL_NEWS_STATE |
| GEOPOLITICAL_RISK | -0.18187 | 6.80644e-09 | 25.6% | 0.0782728 | FAIL | FAIL_NEWS_STATE |

- News-state survivors: None

## Interpretation
- This stage tests incremental information, not trading P&L.
- Same-day external information is excluded by strict as-of alignment.
- Failed news categories are not reworded or reweighted to rescue them.
- A NEWS_STATE_CANDIDATE may enter a later EV test with its query/specification frozen.
