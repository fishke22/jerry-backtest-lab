# Jerry Backtest Lab

Private, cloud-first backtest lab for Nikkei/JNU and Taiwan-stock research.

## Phase 1

Current engine:

- Data: Nikkei official **Nikkei 225 Futures Index** daily series
- Research engine: VectorBT 1.1.0
- Worker: GitHub Actions Free standard Ubuntu runner
- Trigger: push a JSON request under `requests/`
- Outputs: `results/<request_id>.json` and `reports/<request_id>.md`
- Raw Nikkei CSV is fetched at runtime and is **not committed**
- No broker login, no trading, no order execution

## Mobile-first control

Preferred control path:

`ChatGPT GitHub app → requests/*.json → GitHub Actions → results/*.json`

This avoids dependence on a Windows PC or terminal and is intended to remain usable from mobile ChatGPT wherever the GitHub app is available.

See:

- `docs/MOBILE_USAGE.md`
- `docs/VALIDATION_GATES.md`
- `requests/example_sma_walkforward.json`

## Safety / cost guardrails

- Private repository
- Standard GitHub-hosted Ubuntu runner only
- One concurrent backtest job
- 10-minute timeout per run
- No GPU or larger paid runner
- No paid data service is required for Phase 1
- Do not enable paid infrastructure without explicit approval

## Interpretation

Phase 1 validates only **daily directional / regime style modules** using the Nikkei 225 Futures Index proxy.

It does **not** validate JNU-specific intraday behavior such as night-session path, OR15, VWAP, POC/VAH/VAL, OI, basis, roll spread, or micro-contract liquidity.
