# JNU Selection Transition PREPARE-only Dry-Run Seal — 2026-09-08

Status: **CI PASS / PREPARE CHANGESET READY / NOT COMMITTABLE / NO PRODUCTION MUTATION**

## Verification

- Core commit: `4e52724cf3f920be1f46ea89aeb256860aaad52c`
- Integrity run: `34231305690` — PASS
- Actionlint: `34231305657` — PASS
- New PREPARE-only selftest: **40/40 PASS**
- Lifecycle-integrated selection regression: **34/34 PASS**
- Selection-authorization regression: **53/53 PASS**
- Authorization-lifecycle regression: **40/40 PASS**
- Core CI passed on the first attempt; no fix commit was required.
- Stable v1.9 framework SHA: `2e0be163baccd8c42065b088116e313f9e34c39745bbdf509553063d500b1c85`

## PREPARE-only transition contract

The new dry-run changeset binds the immutable lifecycle-integrated decision SHA-256 and backup checksum, lifecycle head SHA-256/event count, exact requested provider/KMS pair, and SHA-256 snapshots of all three authoritative production-state files.

Those three hashes are explicit compare-and-swap preconditions. Stale state fails closed.

The changeset previews the future provider/KMS selection pointers and selected KMS vendor/region/control class, while keeping production enablement false. Provider-term selection readiness remains a separate real-evidence revalidation requirement.

Rollback metadata binds every preimage SHA-256 and requires any future commit protocol to create private preimage backups before production mutation.

This stage supports only `PREPARE_ONLY`. `COMMIT`, `APPLY`, and combined operations are rejected. The generated artifact has `commit_capability=false` and `apply_capability=false`.

The selftest verified that the shortlist, production key profile, and provider-term readiness files are byte-for-byte unchanged after PREPARE.

Public real ledger remains **0 forecasts / 0 outcomes**. Provider/KMS remain **UNSELECTED**.

## Next stage

`PRIVATE_SELECTION_TRANSITION_PREPARE_CHANGESET_DUAL_CONTROL_REVIEW_SYNTHETIC_ONLY`

Build a repo-external synthetic dual-control review gate over an immutable PREPARE-only selection-transition changeset. Require two independent reviewer roles, changeset SHA-256 binding, lifecycle-integrated decision lineage, exact provider/KMS pair binding, revalidation/expiry timestamps, and re-check of all three production-state CAS hashes at review evaluation time. Emit only a redacted review receipt with APPROVE/REJECT/NEEDS_EVIDENCE outcomes; even dual APPROVE must remain NOT_COMMITTABLE with commit_capability=false and apply_capability=false. Reject stale state, expired reviews, reviewer-role conflicts, replay conflicts, pair substitution, tampered changesets, and any attempt to authorize COMMIT/APPLY. Do not mutate shortlist, provider terms, key profile, credentials, KMS resources, or activation state.
