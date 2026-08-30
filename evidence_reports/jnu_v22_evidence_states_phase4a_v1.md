# JNU Evidence-State Validation: jnu_v22_evidence_states_phase4a_v1

## 1. Volatility state
- Best model: **ahar**
- OOS days: 642
- QLIKE improvement vs 20d baseline: 0.082304
- MSE improvement vs 20d baseline: -2.23899e-06
- State gate: **FAIL**

## 2. US tail-risk proxy
- Proxy: Cboe VIX daily close
- OOS days: 642
- Incremental QLIKE improvement: -299204
- Incremental MSE improvement: -2.21675e-08
- State gate: **FAIL**
- Important: VIX is not the same measure as the academic nonparametric tail-risk variable.

## 3. USDJPY conditional state
- 1d / high_vix: n=413, corr=0.110, slope=0.336
- 1d / low_vix: n=480, corr=0.095, slope=0.173
- 5d / high_vix: n=413, corr=-0.026, slope=-0.037
- 5d / low_vix: n=476, corr=0.058, slope=0.051

## Rule
- These tests evaluate information-state value, not a trading strategy.
- Passing states may enter the next EV test with rules frozen.
- Failed states are not re-tuned on this sample.
