# JNU Daily Research Log — 2026-09-06

## V1.7 official prepared-request governance seal

Core commit:

`056d13efdcf9d2b63432a0b852e5c2f8fbd45dac`

GitHub verification:

- JNU Live Shadow V1.7 Integrity Selftest — run `34037173518` — PASS.
- JNU Cloud Workflow Actionlint — run `34037173499` — PASS.
- Official event-source smoke retained from run `33970320931` — PASS.

Real live-shadow ledger remained 0 forecasts / 0 outcomes throughout all amendments and tests.

## New immutable-request preparation gate

The v1.7 chain no longer permits a first-real-capable request to carry a manually selected event state.

The required path is:

1. Start from a quote-free analysis draft.
2. Run `scripts/prepare_jnu_cloud_request_v1.py`.
3. Fetch fresh official target-horizon event evidence.
4. Require the frozen 9-source official coverage set with no unresolved required-source failures.
5. Bind the event-state protocol SHA, request-preparation protocol SHA, request protocol SHA, source coverage, and event state into `risk_state_evidence` and `request_preparation`.
6. Stamp the immutable request only after source retrieval completes.
7. Give the request an exact 900-second validity window.
8. Cloud quote retrieval remains separate and may only use a fresh individual OSE Nikkei 225 Micro contract reference.
9. Preflight v1.1, registrar v1.6, atomic forecast v3, and scorer v1.5 independently recompute the prepared-request provenance.

Handcrafted event state, stale event evidence, missing preparation provenance, protocol-SHA tampering, or incomplete official event source coverage fails closed.

## Official event-source coverage

The official event-state transport remains 9/9:

- BOJ release schedule.
- Statistics Bureau CPI.
- Statistics Bureau Labour Force Survey.
- Statistics Bureau household spending.
- Cabinet Office ESRI general schedule.
- Cabinet Office ESRI GDP schedule.
- U.S. BLS high-impact schedule coverage.
- U.S. BEA release schedule.
- Federal Reserve calendar.

Direct BLS HTTP schedule transport returns 403 in both local and GitHub runner environments. The frozen 2026 fallback is the Executive Office of the President / OMB / OIRA Principal Federal Economic Indicators schedule. The BLS direct failure remains preserved in provenance; the fallback is not represented as a direct BLS response.

The 2026-09-07 smoke reference produced 9/9 source coverage, zero unresolved required-source failures, and `event_state=NORMAL`. This is transport/parser validation only. A real request must regenerate official event evidence within 900 seconds of request creation.

## V1.7 integrity regression

Local preparation-chain selftest: PASS.

Local full-chain integrity selftest: PASS.

Covered failure cases include:

- event UNKNOWN rejected before immutable request creation;
- stale event evidence rejected;
- manually supplied event state rejected;
- handcrafted risk evidence rejected;
- request preparation SHA tampering rejected;
- official event protocol SHA tampering rejected;
- 9/9 source coverage tampering rejected;
- forecast EOL conversion does not break canonical SHA linkage;
- real ledger remains untouched.

Real empty-ledger scorer v1.5: PASS, 0 forecasts / 0 outcomes.

## Current live source blocker

Weekend recheck on 2026-09-06:

- JPX exact Micro: fail closed, approximately 146,904 seconds old; source timestamp `2026-09-05T06:00:00+09:00`.
- TradingView exact Micro: fail closed, approximately 146,905 seconds old; source timestamp `2026-09-05T05:00:00+08:00`.

The frozen maximum remains 900 seconds.

Current blocker:

`INDIVIDUAL_EXACT_MICRO_REFERENCE_FRESHNESS`

NikkeiRealtime continuous Micro remains prohibited as the primary scored reference.

## Formal state

- `VALIDATED_JNU_MODULE = 0`
- `validated_directional_modules = 0`
- `decision_engine = NO_VALIDATED_DIRECTIONAL_EDGE`
- Real ledger = 0 / 0
- No terminal directional family was reopened, retuned, sign-flipped, or rescued.
- No directional/scoring/horizon/confidence/review gate was loosened.


## V1.8 analysis-draft freshness seal

Core commit:

`883d6d71d41a02ca19a713a5b5e2c3469c84cead`

GitHub verification:

- JNU Live Shadow V1.8 Integrity Selftest — run `34038843524` — PASS.
- JNU Cloud Workflow Actionlint — run `34038843503` — PASS.
- JNU Live Shadow V1.7 regression — run `34038843647` — PASS.

V1.8 closes the stale-analysis gap that remained after v1.7. A first-real-capable draft must now carry a unique `draft_id` and offset-aware `analysis_frozen_at_taipei`. The immutable request can be created only when:

`0 <= request_created_at_taipei - analysis_frozen_at_taipei <= 900 seconds`

An expired draft requires a genuinely new analysis draft. Refreshing only the timestamp is prohibited by protocol.

The freshness check is independently revalidated by request preparation, preflight, registration, and scoring. The forecast also preserves the draft protocol SHA and prepared-request validation result.

A cloud/mobile workflow was added at `.github/workflows/jnu-prepare-cloud-request-v1.yml`. It accepts exactly one tracked analysis draft, prevents multiple requests for the same `draft_id`, fetches fresh official event evidence, creates a quote-free immutable request, and commits only that request. No production draft was submitted during this seal.

Local v1.8 full-chain regression: 13/13 PASS, including stale analysis, future analysis, analysis timestamp tamper, and draft-protocol SHA tamper fail-closed cases.

A real official-source preparation smoke for target session 2026-09-07 passed with analysis age 6.956558 seconds, event evidence age 0.219483 seconds, 9/9 official source coverage, `event_state=NORMAL`, and `NEUTRAL_ABSTAIN / LOW`. No real forecast was registered.

Latest weekend exact-Micro source check:

- JPX exact Micro: fail closed at approximately 148,861.7 seconds old.
- TradingView exact Micro: fail closed at approximately 148,862.7 seconds old.
- Frozen maximum remains 900 seconds.

Formal state remains:

- `VALIDATED_JNU_MODULE = 0`
- `validated_directional_modules = 0`
- `decision_engine = NO_VALIDATED_DIRECTIONAL_EDGE`
- Real live-shadow ledger = 0 forecasts / 0 outcomes.
- No terminal-failed directional family was reopened or rescued.
- No directional, scoring, horizon, confidence, quote-freshness, or 30-nonabstain review gate was loosened.


## First-real source readiness orchestration

A read-only first-real launch layer was added without changing the sealed v1.8 directional or scoring semantics.

Core orchestration commit:

`75ea4cab3e43a1e14b9065031bcbf31f15ea7c8d`

Cloud dependency/actionlint fix:

`ee5d3442d6766c04a3c5d51282d0c9f4507b0258`

New components:

- `config/jnu_first_real_launch_protocol_v1.json`
- `scripts/probe_jnu_first_real_source_readiness_v1.py`
- `.github/workflows/jnu-first-real-source-readiness-v1.yml`
- `research_notes/jnu_first_real_launch_runbook_v1.md`

The scheduled workflow probes both allowed individual exact-Micro primary source classes:

- JPX/OSE official exact Micro A.
- TradingView OSE exact Micro B.

It runs five minutes after the official OSE day-session and night-session opening auction times and never creates analysis, an immutable request, a forecast, an outcome, or an order.

Synthetic source-probe selftest: 4/4 PASS, including fresh, stale, engineering failure, and continuous-contract identity rejection.

The first GitHub run `34039345968` correctly failed closed because the stock GitHub Python runner did not contain the `requests` dependency required by the JPX adapter. No ledger mutation occurred. The workflow now installs that dependency explicitly.

The fixed GitHub source-readiness run `34039510168` passed and returned `WAITING_FOR_FRESH_EXACT_MICRO`:

- JPX A: `SOURCE_REACHABLE_STALE`, age 149,588.7 seconds, source `2026-09-05T06:00:00+09:00`.
- TradingView B: `SOURCE_REACHABLE_STALE`, age 149,588.9 seconds, source `2026-09-05T05:00:00+08:00`.
- fresh source count: 0.
- blocker: `INDIVIDUAL_EXACT_MICRO_REFERENCE_FRESHNESS`.
- formal forecast created: false.
- real ledger modified: false.

Expanded cloud Actionlint run `34039498873` passed and now covers the first-real source-readiness workflow, request-preparation workflow, v1.8 integrity workflow, and the existing cloud forecast/request/quote workflows.

The source-readiness schedule is frozen to:

- 08:50 JST day-session probe.
- 17:05 JST night-session probe.

Formal state remains 0 validated directional modules and 0/0 real live-shadow ledger.
