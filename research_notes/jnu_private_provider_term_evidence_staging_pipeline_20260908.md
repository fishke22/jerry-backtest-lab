# JNU Private External Provider-Term Evidence Staging Pipeline

Stage: \`PRIVATE_EXTERNAL_PROVIDER_TERM_EVIDENCE_STAGING_ATTESTATION_PIPELINE_SYNTHETIC_ONLY\`

This stage implements the evidence-handling boundary after the provider questionnaire/intake pack. It deliberately does **not** ingest any real contract, OSE confirmation, provider response, credential, or entitled market data.

The pipeline has two layers:

1. **Private external staging** — a synthetic source document and its synthetic intake metadata must both live outside the public repository. The stage tool verifies raw SHA-256, source class, authority, field-level authority eligibility, structural claim locator, explicitness, reviewer attestation, timezone-aware capture time, and synthetic confidentiality classification.
2. **Redacted attestation emission** — one or more private stage records can be combined. The emitter re-verifies every source document hash, runs the existing frozen term-attestation logic, and writes only the redacted attestation outside the repository. Source document paths and source text are not emitted.

The stage fails closed on real mode, repo-internal source documents, mismatched hashes, non-synthetic URIs, credential-like fields/URIs, invalid source authority, free-text locators, conflicting claims, and post-stage source tampering.

A partial explicit attestation is allowed as an evidence-status artifact, but it does not authorize real backup activation. Vendor selection, outreach, credentials, real entitlement, and real activation remain prohibited in this stage.
