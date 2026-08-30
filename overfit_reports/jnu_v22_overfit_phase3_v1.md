# JNU V2.2 overfit / multiple-testing validation: jnu_v22_overfit_phase3_v1

- Overall status: **NO_MODULE_PASSED_OVERFIT_STAGE**
- Source first engine: suite_results/jnu_v22_daily_proxy_phase2_v1.json
- Source second engine: nautilus_results/jnu_v22_nautilus_phase2_v1.json

| Module | CPCV +paths | CPCV median Sharpe | PBO | DSR P | Holm adj p | Final |
|---|---:|---:|---:|---:|---:|---|
| volatility_regime | 82.1% | 1.161 | 8.6% | 52.7% | 0.1560 | FAIL_OVERFIT_GATES |
| cross_market_confirmation | 46.4% | 0.087 | 97.1% | 64.1% | 0.2419 | FAIL_OVERFIT_GATES |

## Interpretation

- CPCV uses purging and embargo around held-out groups before parameter selection.
- PBO measures how often the in-sample winner falls into the lower half out-of-sample.
- DSR discounts Sharpe for non-normal returns and the number/dispersion of tried parameter configurations.
- Holm-Bonferroni controls family-wise error across the surviving modules.
- This stage intentionally does not search a wider parameter grid to rescue failures.
