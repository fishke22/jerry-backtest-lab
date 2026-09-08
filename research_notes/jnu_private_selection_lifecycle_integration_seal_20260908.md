# JNU Selection Decision × Lifecycle Current-Authorization Integration Seal — 2026-09-08

Status: **CI PASS / CURRENT AUTHORIZATION LIFECYCLE INTEGRATED / NO SELECTION**

## Verification

- Core commit: `79e808467c32b3c12df2fe1f97b4622c37554cb8`
- Integrity run: `34226596411` — PASS
- Actionlint: `34226596470` — PASS
- New lifecycle-integration selftest: **34/34 PASS**
- Prior selection-authorization regression: **53/53 PASS**
- Prior authorization-lifecycle regression: **40/40 PASS**
- Core CI passed on the first attempt; no fix commit was required.
- Stable v1.9 framework SHA: `2e0be163baccd8c42065b088116e313f9e34c39745bbdf509553063d500b1c85`

## Integrated gate

The original selection-authorization gate remains intact and is now wrapped by a stricter lifecycle-current-authorization decision layer.

A decision must prove that the exact authorization artifact ID and SHA-256 is the unique usable current authorization derived from the verified repo-external ISSUE/SUPERSEDE/REVOKE chain at decision time.

The request additionally binds the lifecycle event count and lifecycle head SHA-256. Every lifecycle event must have a checksum-verified immutable backup, and an event dated after the requested decision time is rejected.

Revoked, superseded, expired, missing, tampered, forked, sequence-gapped, parent-lineage-broken, or backup-corrupted lifecycle state cannot authorize a decision.

All base gates remain mandatory: six-pair receipt coverage, twelve current reviews, receipt/composite/pair bindings, disabled synthetic authorization, and unchanged production state.

The only successful status remains `SYNTHETIC_LIFECYCLE_CURRENT_AUTH_VALIDATED_NO_SELECTION`. No provider/KMS pair is selected and no production state is mutated.

Public real ledger remains **0 forecasts / 0 outcomes**.

## Next stage

`PRIVATE_SELECTION_TRANSITION_CHANGESET_PREPARE_ONLY_DRY_RUN_SYNTHETIC_ONLY`

Build a repo-external synthetic PREPARE-only selection-transition changeset over a valid lifecycle-integrated decision record. Bind the decision record SHA-256, lifecycle head SHA-256/event count, exact requested provider/KMS pair, and SHA-256 snapshots of every production-state file that a future authorized selection could modify. Emit an immutable dry-run changeset with explicit intended mutations, compare-and-swap preconditions, rollback/recovery metadata, and commit_capability=false. Reject stale state, pair mismatch, tampered decision records, missing production snapshots, replay conflicts, and any request that attempts COMMIT/APPLY. Do not mutate shortlist, provider terms, key profile, credentials, KMS resources, or activation state; providers/KMS remain UNSELECTED and real activation remains prohibited.
