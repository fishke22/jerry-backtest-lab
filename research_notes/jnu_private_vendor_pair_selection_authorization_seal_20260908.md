# JNU Vendor-Pair Selection Authorization Gate Seal — 2026-09-08

Status: **CI PASS / SYNTHETIC AUTHORIZATION BOUND BUT DISABLED / NO SELECTION**

## Verification

- Core commit: `db8369029d33182bd75b53a6c69d5bc318a03772`
- Integrity run: `34224340047` — PASS
- Actionlint: `34224339861` — PASS
- New selection-authorization selftest: **53/53 PASS**
- Core CI passed on the first attempt; no fix commit was required.
- Stable v1.9 framework SHA: `2e0be163baccd8c42065b088116e313f9e34c39745bbdf509553063d500b1c85`

## Selection boundary now enforced

A vendor-pair decision request now requires two separate repo-external immutable evidence objects:

1. a current dual-control review receipt covering all six market-data-provider × KMS combinations;
2. a separate explicit user-authorization artifact.

Both are SHA-256 bound. The authorization is additionally bound to the review batch, composite dossier SHA-256, and exactly one candidate pair. Pair substitution fails closed.

All twelve reviews in the dual-control receipt must still be current at decision time. The requested pair must retain `SYNTHETIC_DUAL_CONTROL_APPROVED_NOT_ACTIVATABLE` with complete underlying synthetic evidence.

This stage intentionally accepts only:

- `authorization_status = SYNTHETIC_DISABLED`
- `selection_write_permitted = false`
- `real_selection_authorized = false`

Therefore the only successful decision status is `SYNTHETIC_SELECTION_AUTHORIZATION_DISABLED_NO_SELECTION`. Requested candidates may be recorded for audit, but selected provider, selected KMS, and selected combination remain `UNSELECTED`.

The gate re-checks the repository production state and fails closed if shortlist selection, production-key enablement/vendor/region, broker authentication, trading permission, or public-output state has already been mutated.

Decision records are immutable and replay-safe: exact replay is idempotent; the same decision ID with different valid content is rejected.

Public real ledger remains **0 forecasts / 0 outcomes**. No provider or KMS has been selected.

## Next stage

`PRIVATE_VENDOR_PAIR_SELECTION_AUTHORIZATION_REVOCATION_SUPERSESSION_AUDIT_CHAIN_SYNTHETIC_ONLY`

Build a repo-external synthetic authorization lifecycle and change-control audit chain for vendor-pair selection. Add immutable authorization issue/revoke/supersede records, parent-hash lineage, one-current-authorization semantics, explicit revocation reason/state, no silent pair substitution, stale/superseded authorization rejection, and replay/tamper protection. Emit only redacted lifecycle receipts and keep all authorizations disabled, providers/KMS UNSELECTED, production profiles unchanged, and real activation prohibited. Do not contact providers, connect credentials/accounts, create KMS keys, mutate selection/production state, or generate a real activation manifest without explicit user authorization.
