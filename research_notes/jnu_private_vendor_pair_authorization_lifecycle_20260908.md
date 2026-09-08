# JNU Vendor-Pair Selection Authorization Lifecycle / Change-Control Audit Chain

Stage: \`PRIVATE_VENDOR_PAIR_SELECTION_AUTHORIZATION_REVOCATION_SUPERSESSION_AUDIT_CHAIN_SYNTHETIC_ONLY\`

This stage converts synthetic vendor-pair authorization from a single artifact into an append-only lifecycle.

The repo-external lifecycle store contains immutable event files for:
- \`ISSUE\`
- \`SUPERSEDE\`
- \`REVOKE\`

Each event has a contiguous sequence number and a \`parent_event_sha256\`. The current authorization is never stored in a mutable pointer; it is derived by replaying and verifying the full event chain.

Rules:
- \`ISSUE\` is allowed only when there is no active authorization.
- \`SUPERSEDE\` must target the active current authorization and must keep the same vendor pair. A pair change cannot be hidden inside supersession.
- Changing pairs requires an explicit \`REVOKE\` followed by a new \`ISSUE\`.
- \`REVOKE\` must target the active current authorization and requires an explicit reason, user-principal role, and explicit synthetic revocation attestation.
- Superseded and revoked authorizations are never current.
- An expired authorization remains visible in the historical chain but is not usable.

Every ISSUE/SUPERSEDE artifact remains frozen at \`SYNTHETIC_DISABLED\`, with \`selection_write_permitted=false\` and \`real_selection_authorized=false\`.

Exact event replay is idempotent. Reusing an event ID with different request content is rejected. Event-file tampering, missing sequence numbers, broken parent hashes, and backward event time are detected fail-closed.

Lifecycle events redact original authorizer references to SHA-256 references. No selection, production mutation, credential connection, KMS API call, real key creation, or activation authorization is introduced.
