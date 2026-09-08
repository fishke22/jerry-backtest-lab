# JNU Vendor-Pair Selection Authorization Decision Gate

Stage: \`PRIVATE_VENDOR_PAIR_SELECTION_AUTHORIZATION_DECISION_GATE_SYNTHETIC_ONLY\`

This stage creates the boundary between evidence/review completion and any future vendor-pair selection.

A repo-external selection decision request must SHA-256 bind both:
1. a repo-external dual-control review receipt covering all six provider × KMS combinations; and
2. a separate repo-external user-authorization artifact.

The review receipt must remain current at decision time. All twelve underlying reviews must still be before revalidation due and expiry. The requested pair must have the dual-control outcome \`SYNTHETIC_DUAL_CONTROL_APPROVED_NOT_ACTIVATABLE\` and complete underlying synthetic evidence.

The separate authorization artifact is also bound to the review batch, receipt SHA-256, composite dossier SHA-256, and exactly one requested pair. Pair substitution fails closed.

In this stage the only accepted authorization state is deliberately disabled:
- \`authorization_status = SYNTHETIC_DISABLED\`
- \`selection_write_permitted = false\`
- \`real_selection_authorized = false\`

Therefore a fully valid request produces only \`SYNTHETIC_SELECTION_AUTHORIZATION_DISABLED_NO_SELECTION\`. The decision record retains the requested pair for audit but keeps the selected market-data provider, KMS provider, and selected combination at \`UNSELECTED\`.

The gate also re-checks repository production state. Existing provider selection, KMS selection, production-key enablement/vendor/region mutation, broker authentication, trading permission, or public-output request causes fail-closed rejection.

Decision records use a repo-external immutable store. Exact replay is idempotent; the same decision ID with different valid content is rejected.

This stage never contacts providers, connects credentials/accounts, calls a KMS API, creates a key, changes the shortlist/current key profile, or generates a real activation manifest.
