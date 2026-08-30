---
name: mobile-research-orchestrator
description: Coordinate repeatable research from mobile ChatGPT through connected apps and GitHub. Use for backtests, JNU/Nikkei research, Taiwan-stock research, news or sentiment research, scheduled data refreshes, result retrieval, and other workflows that should run in the cloud without a local PC.
compatibility: Designed for ChatGPT/Codex environments with GitHub access and optional external data or workflow apps.
metadata:
  version: "0.1.0"
---

# Mobile Research Orchestrator

Use ChatGPT as the control plane and cloud workers as the execution plane.

## Core rules

1. Prefer connected apps over asking the user to operate a terminal.
2. For reproducible research, write a request file to the private GitHub research repository instead of running ad-hoc local commands.
3. Let GitHub Actions execute deterministic jobs, then read the committed JSON/Markdown results back through the GitHub app.
4. Keep raw market/news data out of Git history unless its license explicitly permits durable storage.
5. Use cloud cache for reusable downloads. Record source URL, retrieval time, checksum, and cache policy.
6. Never promote a candidate research module merely because one backtest is profitable.
7. Preserve failed results and report them as failures.
8. Separate research from execution. Do not log into brokers or place orders.

## Routing

- JNU/Nikkei daily-proxy candidate research -> use the JNU V2.2 daily proxy suite.
- One-off strategy sanity checks -> use the Phase 1 backtest worker.
- News/sentiment research -> route to a dedicated news/sentiment workflow when installed.
- Taiwan-stock research -> route to the Taiwan-stock research workflow when installed.
- Unknown/new domain -> create a scoped workflow specification before adding automation.

## JNU candidate gate

Require, at minimum:

OOS -> walk-forward -> costs -> recent OOS -> bootstrap -> regime analysis.

Only candidates passing those gates become eligible for a second engine. A second-engine pass is still not automatic permission for live trading.

## Data reuse

Prefer this hierarchy:

1. Same-day GitHub Actions cache for raw downloads.
2. Durable derived features/results in the private repo.
3. Durable raw snapshots only when licensing permits.
4. Object storage/data lake later if datasets become too large for the repository.

## Mobile interaction pattern

The user should be able to say what they want in natural language. Convert it into a versioned request file, trigger the appropriate workflow, inspect failures if any, and return the final result without requiring the user's PC.


## Natural-language intent rule

The user is never required to remember command phrases, request schemas, file paths, workflow names, validation jargon, or exact wording.

Interpret ordinary Traditional Chinese natural language semantically. Infer the intended registered workflow from meaning and context. Examples:

- "幫我再測新的日經方法" -> route to the JNU/Nikkei candidate research workflow.
- "把有通過的再做嚴格驗證" -> route only survivors to the next validation stage.
- "看看最近新聞對日經有沒有影響" -> route to news/event research when that workflow exists.
- "重新跑一次，但不要重抓資料" -> use the registered workflow with cloud cache and no forced refresh.

If intent is clear, do not ask the user to restate it using a memorized phrase. Ask a clarifying question only when two materially different workflows or risk levels remain plausible.

Treat this semantic routing rule as a standing interaction contract for mobile use.


## Evidence-first research rule

For new JNU/Nikkei factors, modules, sentiment layers, or parameter families:

1. Search credible academic/empirical evidence first.
2. Separate direct Nikkei evidence from broad-market priors.
3. Translate evidence into a falsifiable hypothesis and a narrow, pre-registered parameter/data plan.
4. Test information value before trading value when the factor is primarily a state variable (volatility, tail risk, news, uncertainty, FX regime).
5. Only after the state/factor adds OOS information may it enter a trading-EV test.
6. Apply costs, recent OOS, CPCV/purge/embargo, PBO/DSR/multiple-testing, and forward OOS before promotion.
7. Never widen a parameter grid or alter thresholds after seeing a failure merely to obtain a pass.
8. Literature support is a prior, not proof of JNU profitability.

For news/sentiment, start as a risk/volatility/confidence state. A direct long/short vote requires separate causal-time-aligned OOS evidence.


## Standing tool-use policy

Treat the following as persistent cross-session operating rules.

1. **Natural-language first**
   - The user should not need to remember tool names, MCP names, workflow IDs, JSON schemas, or command phrases.
   - Infer intent semantically from ordinary Traditional Chinese and route to the appropriate toolchain automatically.

2. **Prefer ChatGPT-connected apps/plugins over local setup**
   - If a connected ChatGPT app/plugin can complete the task, use it before creating a separate local CLI, local daemon, or desktop-only dependency.
   - Favor mobile-compatible paths so the same workflow remains usable from ChatGPT on mobile/web.

3. **Use Skills for reusable reasoning/routing**
   - Skills should hold stable workflow rules, validation logic, routing, evidence standards, and output conventions.
   - Use the mobile research orchestrator as the default router for recurring research tasks.

4. **Use MCP for structured, repeatable data access**
   - Jerry Market Research MCP: J-Quants / FinMind / EODHD / market-research data exposed by the cloud MCP.
   - Use MCP when structured data should be queried repeatedly from ChatGPT without relying on the local PC.
   - Prefer read-only tools and fail closed when a required endpoint/schema is unavailable.

5. **Use GitHub app as the default cloud research control plane**
   - Prefer the ChatGPT GitHub app over GitHub CLI when the app can perform the required operation.
   - GitHub stores code, versioned requests, validation rules, reports, provenance, and durable research decisions.
   - GitHub Actions is the default free cloud worker for deterministic backtests and validation.

6. **Use academic-research apps before inventing new factors**
   - Consensus: primary free academic search/fetch path for literature-backed hypotheses.
   - Scite: cross-check metadata, citation context, open-access availability, and supporting/contrasting evidence.
   - Elicit may be attempted only if available on the current plan; do not upgrade or pay for API access without explicit approval.
   - Evidence-first research should precede new parameter grids.

7. **Cloud data reuse**
   - Reuse existing GitHub Actions cloud cache for market data when possible.
   - Raw data should not be committed to Git by default.
   - Store durable request parameters, source URLs, checksums, derived results, reports, and research decisions in the private repo.
   - Use force-refresh only when freshness is required.
   - If durable large raw-data storage becomes necessary, prefer a free cloud/object-storage option and verify licensing before storing.

8. **News / sentiment workflow**
   - Treat news sentiment as a separate state layer, not a single bullish/bearish scalar.
   - Preserve timestamp, source, language, category, novelty, surprise, intensity, recency, affected session, and regime interaction.
   - Prefer academic evidence and reproducible scoring before using news as a directional trading signal.

9. **JNU research pipeline**
   - Evidence-first -> pre-register -> first-engine OOS/walk-forward/cost/robustness -> overfit/multiple-testing checks -> Nautilus second engine where applicable -> forward OOS.
   - Do not rescue failed modules by widening parameter grids after seeing results.
   - Current research status documents in the repo are authoritative for module promotion/rejection.

10. **Cost and deployment**
    - Prefer free cloud deployment and free-tier tools.
    - Do not enable paid runners, paid data plans, or paid cloud upgrades without explicit user approval.
