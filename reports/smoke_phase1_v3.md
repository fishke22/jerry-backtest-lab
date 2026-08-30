# Backtest: smoke_phase1_v3

- Status: **complete**
- Mechanical validation: **FAIL**
- Promotion status: **CANDIDATE_ONLY**
- Data: 2023-01-04 → 2026-08-28 (894 observations)
- VectorBT: 1.1.0

## Strategy metrics

- Total return: -2.37%
- Annualized return: -0.96%
- Annualized volatility: 27.80%
- Sharpe: 0.105
- Max drawdown: -40.39%
- Hit rate: 50.24%
- Turnover: 20.00

## Benchmark over the same evaluation dates

- Total return: 95.02%
- Sharpe: 1.103
- Max drawdown: -26.04%

## Validation checks

- PASS — min_oos_sharpe
- FAIL — min_oos_total_return
- PASS — min_oos_days
- FAIL — positive_after_cost

## Walk-forward folds

- Fold 0: 2024-01-15 → 2024-04-15 | fast=5 slow=60 | OOS return=10.89% Sharpe=2.404
- Fold 1: 2024-04-16 → 2024-07-17 | fast=5 slow=60 | OOS return=-11.09% Sharpe=-2.596
- Fold 2: 2024-07-18 → 2024-10-18 | fast=20 slow=150 | OOS return=-25.70% Sharpe=-2.550
- Fold 3: 2024-10-21 → 2025-01-23 | fast=10 slow=100 | OOS return=2.26% Sharpe=0.626
- Fold 4: 2025-01-24 → 2025-04-25 | fast=10 slow=100 | OOS return=-1.24% Sharpe=0.039
- Fold 5: 2025-04-28 → 2025-07-29 | fast=10 slow=100 | OOS return=2.25% Sharpe=0.664
- Fold 6: 2025-07-30 → 2025-10-30 | fast=10 slow=60 | OOS return=26.77% Sharpe=4.524
- Fold 7: 2025-10-31 → 2026-02-04 | fast=20 slow=60 | OOS return=5.90% Sharpe=1.131
- Fold 8: 2026-02-05 → 2026-05-13 | fast=20 slow=60 | OOS return=-9.86% Sharpe=-1.044
- Fold 9: 2026-05-14 → 2026-08-12 | fast=10 slow=100 | OOS return=6.66% Sharpe=0.907

## Interpretation limit

This is a daily Futures Index proxy test. It does not validate JNU-specific night-session, intraday volume-profile, basis, roll-spread, OI, or micro-liquidity modules.
