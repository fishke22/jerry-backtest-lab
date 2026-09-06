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
