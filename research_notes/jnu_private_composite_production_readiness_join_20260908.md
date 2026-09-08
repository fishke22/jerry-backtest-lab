# JNU Composite Production-Readiness Evidence Join Gate

Stage: \`PRIVATE_COMPOSITE_PRODUCTION_READINESS_EVIDENCE_JOIN_GATE_SYNTHETIC_ONLY\`

This gate combines the two redacted evidence layers already constructed:

- provider/OSE term attestation;
- KMS deployment-control attestation.

The input is a repo-external synthetic manifest. It must bind exactly all three market-data candidates and all two KMS candidates to repo-external redacted attestation files by SHA-256. Provider attestations currently do not carry a candidate ID, so the manifest requires an explicit synthetic candidate-binding assertion plus reviewer attestation. KMS attestations carry their candidate ID and must match the manifest entry.

The gate verifies exact shortlist coverage, duplicate-free identities, file hashes, artifact classes, synthetic mode, evidence-ledger document hashes, provider-term readiness semantics, KMS control completeness, and the absence of raw source paths, source text, secrets, credentials, and cloud resource identifiers.

It then evaluates the Cartesian product: 3 market-data candidates × 2 KMS candidates = 6 dossiers. No score, rank, recommendation, or selection is generated.

A dossier whose synthetic provider terms and synthetic KMS controls are both complete receives \`SYNTHETIC_PREACTIVATION_EVIDENCE_COMPLETE_NOT_ACTIVATABLE\`, not real readiness. Every dossier still carries immutable activation blockers including synthetic-only evidence, unselected providers, disabled production key profile, disconnected credentials, and no real activation manifest.

This stage never connects accounts, calls KMS APIs, creates keys, mutates the production key profile, selects a provider/KMS pair, or generates a real activation manifest.
