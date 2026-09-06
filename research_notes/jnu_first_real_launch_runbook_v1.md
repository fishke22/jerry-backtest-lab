# JNU First-Real Live-Shadow Launch Runbook v1

Status: pre-first-real, governance-complete, source-freshness-gated.

Authoritative framework: `config/jnu_operational_framework_current_v1_8.json`.

## Read-only source readiness

Use `scripts/probe_jnu_first_real_source_readiness_v1.py` or the scheduled GitHub workflow `.github/workflows/jnu-first-real-source-readiness-v1.yml`.

Allowed primary references:

- JPX/OSE official individual Nikkei 225 Micro month contract — source class A.
- TradingView OSE individual Nikkei 225 Micro month contract — source class B.

Frozen maximum provider-timestamp age: 900 seconds.

NikkeiRealtime continuous Micro is prohibited as the scored primary reference.

The readiness probe is not a forecast. It does not create analysis, a request, a forecast, an outcome, or an order, and it must not modify the real live-shadow ledger.

## Launch sequence after FRESH_SOURCE_AVAILABLE

1. Create a genuinely new analysis draft under `live_shadow_request_drafts/`.
2. The draft must carry a unique `draft_id` and `analysis_frozen_at_taipei`.
3. The analysis must still be at most 900 seconds old when the immutable request is created.
4. Run the cloud request-preparation workflow. It must bind fresh 9/9 official event evidence with zero unresolved required-source failures.
5. The request remains quote-free and is valid for exactly 900 seconds.
6. Run the cloud forecast workflow. It must obtain a fresh individual exact-Micro quote from an allowed source class and pass preflight v1.2.
7. Atomic v4 is the only real forecast write path and requires `--commit-push`.
8. Record the outcome only after the frozen target horizon becomes known.
9. Scorer v1.6 recomputes request, analysis, event, quote, decision-trace, forecast, and outcome integrity.
10. No formal directional validation is allowed until the frozen 30-nonabstain first-review gate is reached.

## Fail-closed rules

Do not register if any of the following applies:

- No allowed individual exact-Micro source is <=900 seconds old.
- Analysis draft is stale or future-dated.
- Official event evidence is stale, incomplete, or UNKNOWN for the first real request.
- Immutable request is expired.
- Quote symbol does not exactly match the request month contract.
- Quote is continuous rather than individual-month Micro.
- Any protocol/hash/provenance check fails.
- The real ledger is not in the expected state.

Do not refresh only a timestamp on an old analysis. Produce a genuinely new analysis.

Do not reopen, flip, retune, or rescue a terminal-failed directional family.

No broker login or order execution is part of this workflow.

## Current pre-first-real state

- VALIDATED_JNU_MODULE = 0
- validated_directional_modules = 0
- decision_engine = NO_VALIDATED_DIRECTIONAL_EDGE
- real forecasts = 0
- real outcomes = 0
