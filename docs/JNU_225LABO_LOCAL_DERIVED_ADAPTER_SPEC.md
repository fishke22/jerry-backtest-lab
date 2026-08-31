# JNU 225Labo Local-Derived Adapter Specification

Status: DESIGN_FROZEN / IMPLEMENTATION_BLOCKED_UNTIL_USER-SUPPLIED_SAMPLE_OR_AUTHORIZED_LOCAL_ACCESS

## Purpose

Use personally licensed 225Labo OSE Nikkei 225 Micro/mini minute data for true-JNU confirmation without uploading raw licensed data or member credentials to third-party cloud services.

## Licensing/security boundary

Raw 225Labo files, member ID, password, session cookies, and download URLs containing authenticated state are **LOCAL_ONLY**.

Prohibited:
- Upload raw minute files to GitHub, Vercel, ChatGPT file storage, or other third-party cloud storage.
- Commit credentials/cookies/tokens to any repository.
- Include raw minute rows in logs, artifacts, diagnostics, or pull requests.
- Reconstruct or redistribute the licensed source data from derived outputs.

Allowed cloud handoff:
- Non-reconstructive daily/session-level derived features.
- Aggregate validation results.
- SHA-256 of the local raw input.
- Source/product identifier, file date/coverage, transform version, and provenance metadata.
- Counts and data-quality diagnostics that do not reveal raw observations.

## Local processing boundary

The local adapter must be a pure file processor in Generation 1. It must **not** automate login/download until a separate credential-handling review is explicitly authorized.

Inputs:
- Explicit local path to a user-downloaded 225Labo JNU or Nikkei mini minute file.
- Instrument identity and contract/product metadata supplied by filename/header or explicit CLI argument.
- Historical OSE session calendar: `config/jnu_session_calendar_versions.json`.

Outputs:
- Daily/session realized-volatility panel only.
- Manifest with input SHA-256, parser version, row counts, coverage, session rules, missingness, duplicate counts, and output SHA-256.
- No raw OHLC rows.

## Frozen HAR-RSV confirmation transform

The true-JNU confirmation must reuse the DI1 method without parameter search:

1. Convert/validate timestamps according to the 225Labo convention.
2. Respect the historically valid OSE session version.
3. Aggregate to 5-minute bars using the frozen aggregation rule.
4. Prevent returns across non-contiguous session breaks.
5. Compute realized variance:
   - `RV_t = sum(r_5m^2)`
6. Compute realized semivariances:
   - `RSV+_t = sum(r_5m^2 * I[r_5m >= 0])`
   - `RSV-_t = sum(r_5m^2 * I[r_5m < 0])`
7. Preserve HAR horizons 1 / 5 / 22.
8. Preserve the existing expanding-OOS and block-bootstrap protocol.
9. No change to sampling interval, HAR horizons, semivariance definition, or pass threshold after seeing JNU results.

## Required data-integrity checks

Fail closed if any of the following is unresolved:
- Instrument identity cannot be determined.
- Contract/date convention is ambiguous.
- Night-session trading-date mapping conflicts with the documented 225Labo/OSE convention.
- Duplicate timestamp policy is unknown.
- Missing intervals exceed a preregistered threshold.
- Session boundaries cannot be mapped to the historical calendar.
- File format differs from the parser's explicitly supported schema.
- Raw input hash changes between derivation and validation.

## Derived export schema

Minimum columns permitted for cloud handoff:
- trading_date
- rv_5m
- rsv_pos_5m
- rsv_neg_5m
- n_5m_returns
- session_coverage_ratio
- source_file_sha256
- transform_version

Optional safe aggregate columns:
- day_session_rv
- night_session_rv
- session-specific RSV values
- data-quality flags

Never export:
- timestamp-level OHLC
- timestamp-level returns
- order/trade records
- credentials or authenticated URLs

## Confirmation decision rule

A proxy-method pass does not become a validated JNU module automatically.

True-JNU HAR-RSV may be admitted only if:
- data-integrity checks pass;
- frozen OOS protocol is completed;
- frozen bootstrap gate passes;
- recent-period behavior does not materially reverse;
- result survives the predeclared loss metrics;
- the role remains volatility/risk-state only unless a separate directional-alpha hypothesis is preregistered.

## Implementation gate

Do not implement a concrete parser until one of the following is available locally:
1. a user-authorized sample 225Labo file; or
2. documented exact file schema sufficient to implement without guessing.

No network login automation is authorized by this specification.


## Confirmation hierarchy across OSE contract sizes

Because Nikkei 225 Micro minute history begins only in 2023 while Nikkei 225 mini minute history is available from 2006, true-OSE confirmation should use a two-stage hierarchy rather than over-rely on the short Micro sample.

### Stage A — long-history OSE mini confirmation
- Preferred long-history source: Nikkei 225 mini minute data from 2006 onward.
- Purpose: test the frozen HAR-RSV volatility/risk-state specification across multiple volatility, policy, crisis and market-structure regimes.
- No parameter search is allowed between the proxy DI1 result and the mini confirmation.
- Historical session/calendar changes must be applied from `config/jnu_session_calendar_versions.json`.

### Stage B — exact-product Micro consistency check
- Source: Nikkei 225 Micro minute data from its 2023 launch onward.
- Purpose: verify that the sign/stability and practical risk-state behavior of the frozen HAR-RSV specification is consistent in the exact target product.
- Because the Micro history is short, Stage B is a consistency/forward confirmation rather than the sole long-history proof.

### Admission rule
HAR-RSV can enter the JNU risk-state layer only if Stage A passes the frozen confirmation gates and Stage B does not materially contradict the result. A Stage A failure cannot be rescued by a positive short Micro sample. A Stage B contradiction requires quarantine and diagnosis rather than parameter retuning.


## Historical-session parser contract

Any future 225Labo Mini/Micro parser MUST load `config/jnu_session_calendar_versions.json` and use the normalized `day_session_segments` / `night_session_segments` fields.

- Nikkei 225 mini history begins 2006-07-18.
- Before 2011-02-14, OSE index futures had separate day segments 09:00-11:00 and 12:30-15:10; 11:00-12:30 is not an active futures interval.
- Evening/night trading began only on 2007-09-18 and was subsequently extended in dated versions.
- The parser must fail closed if an observation date is not covered by an explicit session version.
- Session/version correction is data integrity, never a tunable feature.
- RV/RSV aggregation may include day and night components only according to the trading-day convention valid on that date; do not apply current 2026 hours backward.


## Phase-A tooling status

As of 2026-08-31, the generic schema-audit utility is implemented at:
`scripts/inspect_225labo_local_sample.py`.

It is intentionally not a raw-data parser. It may be run only against a local user-downloaded sample and emits file hash plus structural metadata without raw market rows. Concrete normalization logic remains blocked until the sample's actual workbook/CSV schema is observed and verified.
