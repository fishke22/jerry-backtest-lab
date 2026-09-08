# JNU Selection Decision × Authorization Lifecycle Integration Gate

Stage: \`PRIVATE_SELECTION_DECISION_LIFECYCLE_CURRENT_AUTHORIZATION_INTEGRATION_GATE_SYNTHETIC_ONLY\`

This stage preserves the previously sealed selection-authorization gate and adds a stricter lifecycle-integrated decision layer.

A decision must pass both layers:

1. the existing base selection gate, which verifies the six-pair dual-control receipt, all twelve current reviews, receipt/composite/pair bindings, the separate disabled authorization artifact, and unchanged production state; and
2. the authorization lifecycle gate, which verifies the complete repo-external ISSUE/SUPERSEDE/REVOKE chain and proves that the exact authorization ID + SHA-256 is the unique usable current authorization at decision time.

The integrated request binds to both the lifecycle event count and lifecycle head SHA-256. Every lifecycle event must also have a checksum-verified immutable backup. Events after the decision time are rejected.

Consequences:
- revoked authorization cannot authorize a decision;
- superseded authorization cannot authorize a decision;
- expired authorization cannot authorize a decision;
- a missing chain cannot authorize a decision;
- primary or backup tamper fails closed;
- event sequence gaps, broken parent lineage, and forked/duplicate sequence state fail closed;
- a current authorization for a different pair cannot authorize the requested pair.

The successful synthetic result remains \`SYNTHETIC_LIFECYCLE_CURRENT_AUTH_VALIDATED_NO_SELECTION\`. It does not select a provider/KMS pair, mutate production state, connect credentials, call KMS, create keys, or authorize real activation.
