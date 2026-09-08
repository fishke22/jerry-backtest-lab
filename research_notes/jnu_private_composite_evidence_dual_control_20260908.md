# JNU Composite Evidence Dual-Control Review

Stage: \`PRIVATE_COMPOSITE_EVIDENCE_REVIEW_APPROVAL_DUAL_CONTROL_SYNTHETIC_ONLY\`

This stage reviews the six synthetic pre-activation dossiers produced by the composite join gate.

Each combination requires exactly two independent reviews: one \`EVIDENCE_REVIEWER\` and one \`CONTROL_REVIEWER\`. The reviewers must have different reviewer IDs. Each review binds to the immutable SHA-256 of the full composite dossier file and the canonical SHA-256 of the individual combination dossier.

Allowed dispositions are \`APPROVE\`, \`REJECT\`, and \`NEEDS_EVIDENCE\`. Both reviewers must agree. A mismatch is a conflict and fails closed. Two approvals only produce \`SYNTHETIC_DUAL_CONTROL_APPROVED_NOT_ACTIVATABLE\`, and only when the underlying synthetic dossier is evidence-complete. Approval never selects a provider/KMS pair or authorizes real activation.

Reviews carry reviewed, revalidation-due, and expiry timestamps. Reaching revalidation due or expiry produces a revalidation-required outcome.

Replay handling uses a repo-external immutable receipt store. The canonical receipt path is derived from \`review_batch_id\`. An exact replay is idempotent. Reusing the same batch ID with different receipt content is rejected by immutable-write semantics.

The redacted receipt stores reviewer-role and a reviewer-reference SHA-256, not reviewer IDs. It emits no raw source paths/text, credentials, cloud resource identifiers, ranking, recommendation, selection, key material, or real activation authorization.
