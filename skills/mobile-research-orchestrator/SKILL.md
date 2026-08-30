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
