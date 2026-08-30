# JNU Cross-Session Tooling Policy

Authoritative machine-readable policy: `config/jnu_tooling_policy.json`.

This policy applies to all future JNU / Osaka Nikkei 225 Micro analysis and research.

## Default tool order

1. **Cloud backtesting / repeatable research** — use the private GitHub repo `fishke22/jerry-backtest-lab` and GitHub Actions. Keep requests, manifests, source hashes, results and reports in the repo. Use `.cache/market-data` as reusable cloud cache. Do not make a local Windows file the authoritative backtest record when a cloud workflow exists.
2. **Live chart / session state** — use TradingView Unified MCP / the Nikkei analysis layer when available. Prefer the TRADING and MACRO views plus machine-readable context. If unavailable, use user-provided screenshots or explicitly mark missing data.
3. **Official/current market data** — prefer JPX/OSE, Nikkei Indexes, CME and SGX first-party sources. Jerry Market Research may be used when already configured and it does not introduce a new paid dependency.
4. **Academic evidence** — use available academic plugins/skills such as Consensus, Scite, Elicit and primary-paper web research before adding a factor or module.
5. **Free public intraday proxies** — may be used only for pilot/sanity checks. They are not sufficient for formal JNU module validation.
6. **Local machine / QROS** — Remote Desktop Commander and local files are for inspection, diagnostics and missing-capability bridges. Local-only results must not silently replace the cloud research record.

## Fixed research rules

- Use the current JNU evidence-first architecture and module status system.
- Prefer tools/plugins/skills whenever they materially improve freshness, accuracy or completeness.
- Prefer no-extra-cost options.
- Do not widen lag/parameter grids after seeing results without registering a new trial.
- New modules require preregistered OOS, walk-forward, cost/slippage and multiple-testing/overfit gates before promotion.
- Current/news-sensitive claims require fresh tools/sources rather than memory.
- DPD formal validation requires approved venue-specific OSE/SGX/CME intraday data and identity alignment; proxy-only results remain research-only.

## Storage clarification

The present cloud lab uses GitHub Actions cache for reusable raw downloads. That cache is **not permanent archival storage** and can be evicted. Durable raw object storage has not yet been enabled. Until it is enabled, the durable research record is the request/manifest/provenance hash/result/report in the private GitHub repository.
