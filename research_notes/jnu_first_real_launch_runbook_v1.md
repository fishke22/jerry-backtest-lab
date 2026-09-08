# JNU First-Real Live-Shadow Launch Runbook v1

Status: pre-first-real, governance-complete, source-freshness-gated.

Authoritative framework: `config/jnu_operational_framework_current_v1_9.json`.

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


## Contract rollover

The source-readiness workflow must not hard-code a quarterly-only sequence. JPX specifies Nikkei 225 micro Futures with the nearest two quarterly contract months and the nearest two monthly contract months. The frozen near-term resolver is:

`config/jnu_exact_micro_contract_roll_calendar_v1.json`

with executable resolver:

`scripts/resolve_jnu_exact_micro_contract_v1.py`

Near-term front-month boundaries are frozen as:

- Sep 2026 `NK225MCU2026` through 2026-09-10 16:00 JST.
- Oct 2026 `NK225MCV2026` from 2026-09-10 16:00 JST through 2026-10-08 16:00 JST.
- Nov 2026 `NK225MCX2026` from 2026-10-08 16:00 JST through 2026-11-12 16:00 JST.
- Dec 2026 `NK225MCZ2026` from 2026-11-12 16:00 JST through 2026-12-10 16:00 JST.

The resolver chooses the expected individual contract only. It does not assert that every quote transport currently publishes that month. Source discoverability is checked independently by the source-readiness probe.

As of the 2026-09-06 discovery snapshot:

- Sep/Oct/Nov 2026 are discoverable through both JPX A and TradingView B.
- Dec 2026 is discoverable through TradingView B; the JPX public futures payload used by the adapter does not yet list Dec 2026.

A source-specific missing contract is therefore `CONTRACT_NOT_AVAILABLE_FROM_SOURCE`, not automatically an engineering failure. A fresh quote from another allowed exact-product source can still satisfy the gate.

The frozen calendar exhausts after the Dec 2026 day session. It must fail closed until a new calendar is explicitly frozen; it must never guess a later symbol.

## Sub-900 source feasibility audit — 2026-09-08

The scheduled source-readiness workflow is diagnostic only. A successful workflow conclusion must never be interpreted as `FRESH_SOURCE_AVAILABLE`.

Real scheduled runs on 2026-09-07 returned exact-source ages of 909.1/909.8 seconds (day probe) and 959.6/960.0 seconds (night probe). Both failed the frozen <=900-second source gate.

JPX documents public futures prices as delayed by at least 15 minutes, and TradingView documents free OSE futures data as delayed 15 minutes. Other free/public candidates audited so far either have greater delay, lack Japanese futures API coverage, require authenticated broker service for real-time data, or expose only a continuous Micro instrument.

Authoritative audit: `config/jnu_exact_micro_sub900_source_audit_v1.json`.

Current blocker: `FREE_PUBLIC_EXACT_MICRO_SUB900_SOURCE_NOT_FOUND`.

Do not compensate by loosening the 900-second gate, timestamp-adjusting a delayed feed, or substituting a continuous contract. Reopen first-real launch only when a materially new exact individual-month source demonstrates provider age below 900 seconds with positive operational margin.

## Entitled source contract — sealed 2026-09-08

Core commit: `7c424986e491e92dd8a8cc66acc0881e2263ea76`.

Cloud verification:

- V1.8 Integrity run `34170351493`: PASS.
- Actionlint run `34170351466`: PASS.
- Entitled exact-Micro evidence selftest: **10/10 PASS**.
- Full v1.8 analysis-fresh chain: PASS.
- Empty-ledger scorer: PASS, 0 forecasts / 0 outcomes.

The entitlement layer is now implemented, but no entitled production source exists yet. The validator allows only `OSE_FREE_TRIAL` and `LICENSED_REALTIME_VENDOR` under current governance. Broker-authenticated evidence remains rejected.

The validator is source-only infrastructure: it cannot create a forecast, cannot modify the real ledger, cannot relax the 900-second freshness rule, and cannot substitute a continuous contract.


## Public/private runtime boundary alignment — 2026-09-08

Runtime preflight, registrar, and scorer now hash the authoritative v1.9 framework. Frozen preregistration/implementation v1.7 remain unchanged because their directional/scoring semantics are historical and v1.9 explicitly preserves them.

The default real ledger under `live_shadow/forecasts` is a public Git repository path. `scripts/register_jnu_operational_shadow_forecast_atomic_v4.py` therefore invokes `scripts/validate_jnu_public_live_shadow_boundary_v1.py` before any real write. Any OSE Free Trial, licensed realtime vendor, authorized broker-feed entitlement marker, private-raw marker, or secret-like field is rejected from this public path.

The cloud forecast workflow also runs `scripts/check_jnu_public_artifact_safety_v1.py` before uploading diagnostic artifacts. Unsafe entitled/private artifacts are not uploaded.

This does not make entitled data production-ready. It prevents accidental public leakage while a future private evidence bridge is designed and while OSE/provider cloud/publication permissions remain unresolved.
