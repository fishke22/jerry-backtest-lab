# JNU Selection Transition PREPARE Changeset Dual-Control Review

Stage: \`PRIVATE_SELECTION_TRANSITION_PREPARE_CHANGESET_DUAL_CONTROL_REVIEW_SYNTHETIC_ONLY\`

This stage places an independent two-person review gate over an immutable PREPARE-only selection-transition changeset.

Required reviewer roles:
- \`CHANGE_REVIEWER\`
- \`CONTROL_REVIEWER\`

The reviewer IDs must be different. Each review binds the PREPARE changeset SHA-256, lifecycle-integrated decision SHA-256, and exact provider/KMS pair, and carries reviewed/revalidation/expiry timestamps plus explicit reviewer attestation.

At review evaluation time the gate re-opens both immutable repo-external artifacts and verifies their backup checksums. It revalidates decision lineage through decision ID, decision SHA, lifecycle head SHA, lifecycle event count, and pair identity.

It also recomputes SHA-256 for the three authoritative production-state files and compares them with the CAS hashes frozen into PREPARE. A state change after PREPARE therefore yields \`SYNTHETIC_DUAL_CONTROL_STALE_STATE_BLOCKED_PREPARE\`.

Outcomes:
- dual APPROVE -> \`SYNTHETIC_DUAL_CONTROL_APPROVED_PREPARE_NOT_COMMITTABLE\`
- dual REJECT -> rejected
- dual NEEDS_EVIDENCE -> needs evidence
- mixed dispositions -> conflict blocked
- stale/expired reviews -> revalidation required
- stale production state -> stale-state blocked

Even dual APPROVE cannot commit or apply. The review receipt keeps \`commit_capability=false\`, \`apply_capability=false\`, \`selection_written=false\`, and production state unchanged.
