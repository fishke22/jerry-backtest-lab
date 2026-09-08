# JNU Selection Transition Changeset — PREPARE-only Dry Run

Stage: \`PRIVATE_SELECTION_TRANSITION_CHANGESET_PREPARE_ONLY_DRY_RUN_SYNTHETIC_ONLY\`

This stage adds a non-committable transition-planning artifact over a valid lifecycle-integrated selection decision.

The PREPARE request binds:
- immutable lifecycle-integrated decision record SHA-256 and backup checksum;
- lifecycle head SHA-256 and event count;
- exact requested provider/KMS pair;
- SHA-256 snapshots of the three authoritative production-state files:
  - provider selection shortlist;
  - production key custody current;
  - provider term readiness current.

The three file hashes are compare-and-swap preconditions. Any stale snapshot fails closed.

The output contains a preview of future selection intent, not an executable patch. It records the requested provider/KMS selection pointers and the selected KMS vendor/region/control-class preview while keeping \`production_enabled=false\`. Provider-term selection readiness is explicitly marked as requiring separate real evidence revalidation before any future commit.

Rollback/recovery metadata binds each production preimage SHA-256 and requires a future commit protocol to create private preimage backups before changing production state. PREPARE itself creates no production backup because it writes no production state.

Only \`operation=PREPARE_ONLY\` is accepted. \`COMMIT\`, \`APPLY\`, and combined operations are rejected. The immutable changeset states \`commit_capability=false\` and \`apply_capability=false\`.

No shortlist, provider-term, key-profile, credential, KMS resource, key, or activation state is modified.
