# Nautilus second-engine validation: jnu_v22_nautilus_phase2_v1

- NautilusTrader: 1.231.0
- Source suite: suite_results/jnu_v22_daily_proxy_phase2_v1.json
- Source hashes match: **True**
- Overall status: **PASS_SECOND_ENGINE**

## Modules

| Module | Status | Position match | Fills expected/actual | Max fill px error | Commission JPY |
|---|---|---:|---:|---:|---:|
| volatility_regime | PASS_ENGINE_REPLAY | 100.0% | 76/76 | 0.000000 | 1001.00 |
| cross_market_confirmation | PASS_ENGINE_REPLAY | 100.0% | 135/135 | 0.000000 | 1890.00 |

## Scope

- This second engine does not re-select parameters.
- It independently rebuilds the two causal signal formulas from the published walk-forward fold parameters.
- It verifies Nautilus event sequencing, active OOS position state, market-fill count, current-bar fill price, and fee accounting.
- Commission plus requested slippage is represented as an equivalent taker fee because daily close-only proxy bars cannot identify a real bid/ask slippage path.
- PASS_ENGINE_REPLAY is not VALIDATED_JNU_MODULE. Purged/CPCV and multiple-testing/overfit diagnostics remain before promotion.
