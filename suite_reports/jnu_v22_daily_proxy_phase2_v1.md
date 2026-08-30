# JNU V2.2 Daily Proxy Suite: jnu_v22_daily_proxy_phase2_v1

- Data: 2023-01-04 -> 2026-08-28 (894 observations)
- VectorBT: 1.1.0
- Candidate modules: 6
- Eligible for second engine: 2

## Summary

| Module | Status | OOS return | Sharpe | Max DD | Recent | 2x cost | +folds | +regimes | Bootstrap P+ |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| trend_momentum | FAIL | -58.42% | -1.124 | -71.16% | 20.60% | -59.84% | 50% | 0% | 4.6% |
| breakout | FAIL | 2.73% | 0.178 | -36.24% | 5.56% | 2.32% | 40% | 50% | 61.2% |
| volatility_regime | PASS_CANDIDATE | 28.88% | 0.899 | -21.48% | 10.65% | 26.53% | 70% | 50% | 92.6% |
| drawdown_repair | FAIL | -4.56% | -0.276 | -13.24% | 1.96% | -4.88% | 30% | 50% | 24.8% |
| relative_strength_ndx | FAIL | -63.27% | -1.304 | -71.89% | -1.48% | -64.23% | 20% | 0% | 2.6% |
| cross_market_confirmation | PASS_CANDIDATE | 22.13% | 0.443 | -36.75% | 23.68% | 18.05% | 70% | 75% | 81.2% |

## Second-engine queue

- volatility_regime
- cross_market_confirmation

## Interpretation limits

- These are daily proxy tests, not JNU intraday validation.
- NDX and USDJPY are aligned so their day-t observations can only affect the next Nikkei trading-day position.
- Raw downloaded source files are cloud-cached and are not committed to Git.
- A PASS_CANDIDATE is only eligible for a second engine; it is not a VALIDATED_JNU_MODULE.
