# JNU MACD Stage A pre-outcome reconciliation — 2026-09-01

Status: PRE_OUTCOME_GOVERNANCE_AND_DATA_INTEGRITY_RECONCILED / LOCAL_RAW_BUILD_BLOCKED_DEVICE_OFFLINE

## Canonical active family
`MACD_4_22_3_POSTPUBLICATION_TRUE_JNU_G1`

Canonical preregistration: `config/jnu_macd_4_22_3_postpublication_g1_prereg.json`.

This family remains the single active formal directional family. It freezes MACD(4,22,3), one-close execution lag, 2022-08-01 through 2023-07-21 OSE Mini Stage A evaluation, minimum 200 days, positive mean gross strategy return, accuracy > 0.5, and 5-day moving-block bootstrap P(mean>0) >= 0.95.

## Duplicate-family reconciliation
A later same-session family named `MACD_4223_POST_PUBLICATION_TRUE_JNU_G1` was created minutes after the canonical family. No Stage A market outcome was inspected under either family.

Disposition: `GOVERNANCE_DUPLICATE_NO_OUTCOME_NOT_A_SEPARATE_ATTEMPT`.

It must not be counted as a second logical family or used to choose between alternative execution/bootstrap definitions after outcomes. The earlier canonical family is retained because it already conforms to the standing JNU governance requirement for moving-block bootstrap and explicitly freezes the execution lag.

## DI1 before outcome
The canonical local adapter originally constructed session minutes with an exclusive Python range. Under `config/jnu_session_calendar_versions.json`, the Stage-A period day session ends at 15:15; the preregistration requires the final day-session one-minute close. Exclusive construction would therefore select the prior minute.

DI1 changes the session-end minute to inclusive and records transform version `JNU_MACD_4_22_3_POSTPUBLICATION_G1_V1_DI1_FINAL_MINUTE_INCLUSIVE`.

Commit: `d92c0c1d31f685ae23fe3cb0d0126dc4d64ebb74`.

This is a data-integrity correction only. No MACD parameter, signal logic, execution lag, evaluation boundary, minimum sample size, bootstrap block length, bootstrap seed/resamples, or PASS threshold changed.

## Current blocker and next action
Remote Desktop Commander reported no authorized online device during this session. Therefore 225Labo raw was not read and no Stage A outcome was generated.

When the device is online, the next action is exactly:
1. Use local-only 225Labo Mini raw.
2. Build the canonical non-reconstructive Stage-A panel with the DI1 adapter.
3. Verify Gate 0: source identity/hash, final-minute/session coverage, no critical DQ, output hash, and `market_outcome_interpretation_performed=false`.
4. Persist only the allowed derived panel/manifest to GitHub.
5. Dispatch `.github/workflows/jnu-macd-4-22-3-mini-stage-a-g1.yml` once.
6. If Stage A FAILS, close the family permanently and prohibit exact-JNU Stage B rescue. If PASS, proceed to exact-JNU Micro Stage B without retuning.

Decision engine remains `NO_VALIDATED_DIRECTIONAL_EDGE` until downstream promotion gates are completed.