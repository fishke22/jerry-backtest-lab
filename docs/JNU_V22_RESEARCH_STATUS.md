# JNU V2.2 Research Status

Updated: 2026-08-30

## Standing interpretation

No module is currently a `VALIDATED_JNU_MODULE`.

| Module | First engine | Nautilus second engine | Overfit / multiple testing | Research disposition |
|---|---|---|---|---|
| volatility_regime | PASS_CANDIDATE | PASS_ENGINE_REPLAY | FAIL_OVERFIT_GATES | QUARANTINE / independent confirmation only |
| cross_market_confirmation | PASS_CANDIDATE | PASS_ENGINE_REPLAY | FAIL_OVERFIT_GATES | REJECT_OVERFIT |
| trend_momentum | FAIL | not eligible | not run | REJECT |
| breakout | FAIL | not eligible | not run | REJECT |
| drawdown_repair | FAIL | not eligible | not run | REJECT |
| relative_strength_ndx | FAIL | not eligible | not run | REJECT |
| SMA baseline | FAIL | not eligible | not run | BASELINE_ONLY |

## Why volatility_regime is quarantined rather than promoted

It showed strong structural robustness under CPCV and low PBO, but did not clear the pre-registered Deflated Sharpe Ratio or family-wise multiple-testing significance thresholds. It may be tested on genuinely independent data with the rules frozen, but it must not be tuned against the same 2023-2026 sample to force a pass.

## Why cross_market_confirmation is rejected

Its PBO was extremely high and CPCV positive-path consistency was below the required threshold. The apparent first-engine and second-engine profitability is therefore not sufficient evidence of a durable edge.

## Rule

Do not rescue failed modules by widening parameter grids, changing thresholds after seeing results, or selectively dropping bad periods. A new hypothesis must be pre-registered as a new research candidate.
