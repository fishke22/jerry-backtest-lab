# JNU Daily Research Log — 2026-09-04

## Exact-Micro source provenance and primary-reference gate

NikkeiRealtime protocol research reached a source-governance disposition. The public transport exposes `N225MC.FUT.OSE.CONT` with source-carried timestamps, but no individual month Micro identifier was found. Direct same-timestamp cross-mapping to `OSE:NK225MCU2026` also produced mismatch evidence, so the continuous contract is not an admissible substitute for the individual Sep-2026 contract. It remains B-grade context/cross-check only.

TradingView exact individual OSE Micro support is operational through `lp_time`, `source_id=OSE`, exact Micro identity, and delayed-streaming metadata. The frozen reference-age gate remains 900 seconds. A live observation checked during this session was about 935.7 seconds old and was rejected.

An official JPX/OSE public exact-Micro adapter was added for the individual Sep-2026 contract. The public payload identifies the Micro product and listed contract, and carries the Last price timestamp at minute precision. Conservative timestamp interpretation uses second 00; delay is never waived. Live checks observed stale ages including 916.9 and 905.6 seconds, so no real forecast was registered.

## Operational Framework v1.5 governance

Commit `81ca39a` froze the v1.5 multi-source exact-Micro governance: JPX official exact Micro is source class A, TradingView exact individual OSE Micro is source class B, and both still require actual age <=900 seconds. Framework/prereg/implementation/protocol SHA chain remains:
- framework: `797fa0ccb7a5bcf0d05e59e60106dd807073450e992061cc406f39999932ea51`
- prereg: `e13dd67e9bcc5a22b43bd13a038d0087e4fdc62f163a3ff38ca9f499faa113f7`
- implementation: `cd44c7c7a13ed67263edbfb7f129d467ab9ef9c8d1ef8779f0286a4d43017b95`
- protocol: `fe10aca973f2038fcd2038ae9564253e58685c6d40f79a88d54f44f828a0d552`

The original decision-protocol regression and all three UNKNOWN fail-safe cases were rerun and passed. Event UNKNOWN still forces `NEUTRAL_ABSTAIN`; HAR/SQ UNKNOWN cap confidence to LOW.

## Cloud execution alignment

The cloud request builder now validates both frozen source classes through the shared source validator. The live-shadow cloud workflow now selects JPX official first and TradingView second, with each observation independently required to pass the same <=900-second gate. GitHub Actionlint run `33876057519` passed. A synthetic JPX-A request passed cloud-builder -> atomic-registration selftest without touching the real ledger.

## Current formal state

Real live-shadow ledger remains 0 forecasts / 0 outcomes. No first real forecast was created because the allowed live observations inspected during this checkpoint failed the frozen freshness gate. `VALIDATED_JNU_MODULE=0`, validated directional modules remain 0, and the decision engine remains `NO_VALIDATED_DIRECTIONAL_EDGE`. No terminal-failed directional family was reopened or retuned.

## Final live-source recheck

After final integrity checks, both frozen primary candidates were retried. JPX official Sep-2026 Micro was rejected at 949.9 seconds age, and TradingView individual `NK225MCU2026` was rejected at 950.6 seconds age. Both exceed the unchanged 900-second gate. The real ledger therefore remains 0/0 and the event-state gate was not advanced because the prerequisite exact-reference freshness gate did not pass.
