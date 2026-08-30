# JNU Dynamic Price Discovery Cloud Pilot — jnu_dpd_cloud_pilot_v1

- Status: **PILOT_ONLY_INSUFFICIENT_VENUE_COVERAGE**
- Execution: GitHub Actions cloud runner
- Raw downloads: GitHub Actions cloud cache only; not committed
- Formal validation: **NOT ALLOWED** because OSE/SGX venue-specific intraday data are not present

## Fixed preregistered design
- Intervals: 1m, 5m
- Maximum lead/lag: ±3 bars
- Chronological train fraction: 70%
- States: JP_CASH and US_CASH
- No post-hoc lag-window widening in this run

## Comparison summary
- 1m / JP_CASH / ES_to_NIY: strongest nonzero lead=1 bars, corr=0.1130, OOS MSE Δ=1.054%, hit Δ=0.706pp, test_days=2
- 1m / JP_CASH / NQ_to_NIY: strongest nonzero lead=1 bars, corr=0.1406, OOS MSE Δ=2.774%, hit Δ=5.412pp, test_days=2
- 1m / JP_CASH / NIY_to_ES: strongest nonzero lead=-1 bars, corr=0.1130, OOS MSE Δ=-2.144%, hit Δ=-1.412pp, test_days=2
- 1m / US_CASH / ES_to_NIY: strongest nonzero lead=1 bars, corr=0.0573, OOS MSE Δ=-0.088%, hit Δ=4.405pp, test_days=2
- 1m / US_CASH / NQ_to_NIY: strongest nonzero lead=1 bars, corr=0.0673, OOS MSE Δ=-2.045%, hit Δ=2.496pp, test_days=2
- 1m / US_CASH / NIY_to_ES: strongest nonzero lead=-1 bars, corr=0.0573, OOS MSE Δ=0.015%, hit Δ=-0.441pp, test_days=2
- 1m / JP_SAME_UNDERLYING_PROXY / NIY_to_N225: strongest nonzero lead=-1 bars, corr=0.0773, OOS MSE Δ=0.769%, hit Δ=1.425pp, test_days=2
- 1m / JP_SAME_UNDERLYING_PROXY / N225_to_NIY: strongest nonzero lead=1 bars, corr=0.0773, OOS MSE Δ=-2.027%, hit Δ=2.850pp, test_days=2
- 1m / JP_SAME_UNDERLYING_PROXY / NIY_to_NKD: strongest nonzero lead=1 bars, corr=0.1745, OOS MSE Δ=8.976%, hit Δ=9.375pp, test_days=2
- 1m / JP_SAME_UNDERLYING_PROXY / NKD_to_NIY: strongest nonzero lead=-1 bars, corr=0.1745, OOS MSE Δ=0.009%, hit Δ=-1.562pp, test_days=2
- 5m / JP_CASH / ES_to_NIY: strongest nonzero lead=-2 bars, corr=-0.0213, OOS MSE Δ=0.113%, hit Δ=0.428pp, test_days=15
- 5m / JP_CASH / NQ_to_NIY: strongest nonzero lead=-1 bars, corr=0.0200, OOS MSE Δ=0.038%, hit Δ=1.285pp, test_days=15
- 5m / JP_CASH / NIY_to_ES: strongest nonzero lead=2 bars, corr=-0.0213, OOS MSE Δ=-0.005%, hit Δ=0.107pp, test_days=15
- 5m / US_CASH / ES_to_NIY: strongest nonzero lead=2 bars, corr=0.0631, OOS MSE Δ=-0.048%, hit Δ=-0.771pp, test_days=15
- 5m / US_CASH / NQ_to_NIY: strongest nonzero lead=-2 bars, corr=0.0754, OOS MSE Δ=-0.052%, hit Δ=-2.057pp, test_days=15
- 5m / US_CASH / NIY_to_ES: strongest nonzero lead=-2 bars, corr=0.0631, OOS MSE Δ=-0.345%, hit Δ=-0.428pp, test_days=15
- 5m / JP_SAME_UNDERLYING_PROXY / NIY_to_N225: strongest nonzero lead=1 bars, corr=0.0169, OOS MSE Δ=-1.880%, hit Δ=-2.578pp, test_days=15
- 5m / JP_SAME_UNDERLYING_PROXY / N225_to_NIY: strongest nonzero lead=-1 bars, corr=0.0169, OOS MSE Δ=-0.381%, hit Δ=2.242pp, test_days=15
- 5m / JP_SAME_UNDERLYING_PROXY / NIY_to_NKD: strongest nonzero lead=-1 bars, corr=-0.0251, OOS MSE Δ=5.211%, hit Δ=4.336pp, test_days=15
- 5m / JP_SAME_UNDERLYING_PROXY / NKD_to_NIY: strongest nonzero lead=1 bars, corr=-0.0251, OOS MSE Δ=-0.037%, hit Δ=0.394pp, test_days=15

## Interpretation guardrail
- Same-bar correlation is not treated as a tradable lead.
- A positive one-bar association is not promoted unless it survives longer OOS, costs, venue alignment, and multiple-testing gates.
- Yahoo symbols are provisional public-web proxies, not authoritative OSE/SGX contract data.

## Promotion gate
- PASS: **False**
- Reason: Required OSE and SGX venue-specific intraday data are absent. This run is a cloud pilot only.
