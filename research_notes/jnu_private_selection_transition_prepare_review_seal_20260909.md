# JNU PREPARE Changeset Dual-Control Review Seal — 2026-09-09

Status: **CI PASS / DUAL CONTROL REVIEWED / STILL NOT COMMITTABLE**

## Verification

- Core commit: `58f2d3ed6b4c4be4e31665e399025b394ff8642a`
- Integrity run: `34284041237` — PASS
- Actionlint: `34284041211` — PASS
- New PREPARE dual-control review selftest: **47/47 PASS**
- PREPARE regression: **40/40 PASS**
- Lifecycle-integrated decision regression: **34/34 PASS**
- Selection authorization regression: **53/53 PASS**
- Authorization lifecycle regression: **40/40 PASS**
- Core CI passed on the first attempt; no fix commit was required.
- Stable v1.9 framework SHA: `2e0be163baccd8c42065b088116e313f9e34c39745bbdf509553063d500b1c85`

## Dual-control review now enforced

An immutable PREPARE-only changeset now requires two independent reviews: `CHANGE_REVIEWER` and `CONTROL_REVIEWER`.

Each review binds the changeset SHA-256, lifecycle-integrated decision SHA-256, and exact provider/KMS pair. Review time, revalidation due time, and expiry time are all enforced.

At evaluation time the gate re-verifies both immutable artifact backups, decision lineage, lifecycle head/count, and recomputes all three production-state SHA-256 values against the CAS hashes frozen into PREPARE.

A state drift after PREPARE blocks approval. Stale or expired reviews require revalidation. Mixed dispositions are conflict-blocked.

Even dual APPROVE yields only `SYNTHETIC_DUAL_CONTROL_APPROVED_PREPARE_NOT_COMMITTABLE`.

The receipt has `commit_capability=false` and `apply_capability=false`. Reviewer IDs are redacted to SHA-256 references.

The selftest verified the three authoritative production-state files remain byte-for-byte unchanged.

Public real ledger remains **0 forecasts / 0 outcomes**. Provider/KMS remain **UNSELECTED**.

## Next stage

`PRIVATE_SELECTION_TRANSITION_COMMIT_AUTHORIZATION_CEREMONY_GATE_SYNTHETIC_DISABLED_ONLY`

Build a repo-external synthetic commit-authorization ceremony over a valid non-expired PREPARE dual-control review receipt. Bind the review receipt SHA-256, PREPARE changeset SHA-256, lifecycle-integrated decision SHA-256, lifecycle head/count, exact provider/KMS pair, and all three production-state CAS hashes. Require a distinct explicit USER_PRINCIPAL commit-authorization artifact, but in this stage accept only SYNTHETIC_DISABLED with commit_authorized=false, apply_authorized=false, and no execution capability. Revalidate review freshness and CAS state at ceremony evaluation time. Reject stale/expired review receipts, stale production state, pair substitution, tamper, replay conflict, inferred authorization, or any artifact claiming COMMIT/APPLY enabled. Do not mutate shortlist, provider terms, key profile, credentials, KMS resources, or activation state.
