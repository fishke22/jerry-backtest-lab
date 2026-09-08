# JNU Selection Transition Commit-Authorization Ceremony

Stage: \`PRIVATE_SELECTION_TRANSITION_COMMIT_AUTHORIZATION_CEREMONY_GATE_SYNTHETIC_DISABLED_ONLY\`

This stage adds a distinct USER_PRINCIPAL authorization ceremony after PREPARE dual-control review.

The ceremony re-opens and checksum-verifies the immutable review receipt, PREPARE changeset, and lifecycle-integrated decision. It binds review receipt SHA-256, changeset SHA-256, decision SHA-256, exact provider/KMS pair, lifecycle head/count, and the three production-state CAS hashes.

The review receipt must still be dual APPROVE and every review must remain before revalidation due/expiry at ceremony evaluation time. The three production state hashes are recomputed again.

The separate USER_PRINCIPAL artifact is accepted only with:
- \`authorization_status=SYNTHETIC_DISABLED\`
- \`commit_authorized=false\`
- \`apply_authorized=false\`
- \`execution_capability=false\`

Therefore explicit user-principal ceremony evidence does not grant execution in this stage. Any artifact claiming enabled commit/apply/execution is rejected.

The output is immutable and redacts the raw authorizer reference to a SHA-256 reference. No production state is modified.
