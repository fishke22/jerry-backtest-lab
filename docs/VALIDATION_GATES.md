# Validation gates

Phase 1 is a daily-close proxy lab for JNU/Nikkei research.

A candidate is not a validated JNU module merely because the backtest is profitable.

Minimum interpretation rules:

1. No look-ahead: positions are shifted by one trading day.
2. Costs: every position change is charged requested commission + slippage in basis points.
3. Walk-forward: parameter selection occurs only on the training window; reported OOS returns come only from following test windows.
4. A result marked PASS only satisfies the mechanical thresholds in the request. It is still only a candidate.
5. JNU-specific intraday modules such as night-session path, OR15, VWAP, POC/VAH/VAL, OI, basis, roll spread and micro-contract liquidity are NOT validated by this daily Futures Index proxy.
6. Before promotion to VALIDATED_JNU_MODULE, require independent review, multiple regimes, recent effectiveness, cost robustness, and preferably a second engine.

The official Nikkei 225 Futures Index is used as a daily directional proxy for OSE Nikkei 225 futures. Raw source CSV is fetched at runtime and is not committed to this repository.
