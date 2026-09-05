# JNU Daily Research Log — 2026-09-05

## V1.6 governance seal

- Core seal commit: `6334f8477142efccfbf3470b7a45d1bab2e0d3cd`.
- GitHub cloud request selftest: run `33969428203` — PASS.
- GitHub workflow actionlint: run `33969428165` — PASS.
- Real live-shadow ledger remained 0 forecasts / 0 outcomes throughout the amendment.
- No terminal-failed directional family was reopened, retuned, or rescued.
- Directional/scoring/horizon/confidence/review thresholds were unchanged.

## New first-registration integrity gates

- Immutable request validity <= 900 seconds and forecast creation must occur inside the request window.
- Individual exact OSE Nikkei 225 Micro contract identity must match the source metadata.
- Exact-Micro provider timestamp age remains <= 900 seconds; no relaxation.
- Risk-state evidence must match the frozen decision trace and target date.
- Risk-state evidence and known event-source checks must be <= 900 seconds old at both request and forecast creation.
- First real forecast registration is blocked if target-horizon event state is UNKNOWN.
- HAR/SQ UNKNOWN remain non-directional confidence caps under the frozen decision protocol.

## Cross-platform integrity fix

Windows `core.autocrlf=true` caused raw-byte SHA256 to differ from the Git/Linux blob for unchanged text. The v1.6 chain therefore freezes `SHA256_TEXT_EOL_CRLF_V1`: normalize logical text line endings to CRLF before SHA256. No whitespace trimming, JSON reserialization, Unicode normalization, key reordering, or numeric normalization is permitted. Binary evidence remains raw-byte SHA256.

This preserves the pre-first-forecast frozen decision-protocol SHA:
`fe10aca973f2038fcd2038ae9564253e58685c6d40f79a88d54f44f828a0d552`.

A full synthetic chain passed after deliberately converting the immutable forecast record from Windows-style EOL to LF-only between outcome recording and scoring.

## Current formal state

- `VALIDATED_JNU_MODULE = 0`
- `validated_directional_modules = 0`
- `decision_engine = NO_VALIDATED_DIRECTIONAL_EDGE`
- Real ledger = 0 / 0
- Current external blocker remains `INDIVIDUAL_EXACT_MICRO_REFERENCE_FRESHNESS`.
- NikkeiRealtime continuous Micro remains prohibited as a primary scored reference.
