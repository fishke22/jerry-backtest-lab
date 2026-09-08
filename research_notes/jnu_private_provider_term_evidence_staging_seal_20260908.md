# JNU Private External Provider-Term Evidence Staging Seal — 2026-09-08

Status: **CI PASS / SYNTHETIC EXTERNAL STAGING READY / REAL EVIDENCE BLOCKED**

This stage implements the private external provider/OSE term-evidence staging boundary without ingesting any real contract, confirmation, credential, or entitled market data.

## Commits and CI

- Core commit: `2ecb7ecc62db80224f8985ee853639bed204e7bd`
- Core integrity run: `34222419778` — failed only because the selftest substring-matched the legal metadata key `source_document_paths_emitted`
- Fix commit: `a188f27387addcd9c6c6bde21f0e1435b2fdbea6`
- Final integrity run: `34222506066` — PASS
- Actionlint: `34222419797` — PASS
- New staging selftest: **24/24 PASS**
- Stable v1.9 framework SHA: `2e0be163baccd8c42065b088116e313f9e34c39745bbdf509553063d500b1c85`

No safety rule was relaxed by the fix. The emitter already prohibited exact `source_document_path` keys; only the test was corrected to inspect exact keys rather than substrings.

## Enforced boundary

Synthetic source documents, intake metadata, staging records, and current-stage redacted outputs must be outside the public repository. The pipeline verifies raw SHA-256, re-verifies the source hash at emission, validates source class and authority against the frozen term protocol, enforces per-field authority, compact structural locators, explicit reviewer attestation, and synthetic confidentiality labels.

It fails closed on real mode, repo-internal source files, non-synthetic URIs, credential-like metadata, wrong SHA, wrong authority, free-text locators, real confidentiality labels, inferred reviewer claims, source tampering after staging, and conflicting cross-stage claims.

The redacted output keeps only field-level provider-term status plus evidence ID/authority/class/URI/hash/locator metadata. It emits no source path, source text, credentials, or real-activation authorization.

## Regression state

All prior regressions remain PASS, including v1.9 supersession 17/17, quote evidence 13/13, storage boundary 9/9, public guards 8/8 + 4/4, private quote bridge 10/10, private live shadow 16/16, lifecycle 19/19, concurrency/DR/state 18/18, encrypted backup 30/30, production key/provider-term 30/30, shortlist/activation 11/11, and provider evidence intake 16/16.

Public real ledger remains **0 forecasts / 0 outcomes**. Real entitlement remains **not connected**.

## Next stage

`PRIVATE_KMS_DEPLOYMENT_EVIDENCE_STAGING_CONTROL_ATTESTATION_PIPELINE_SYNTHETIC_ONLY`

Build a repo-external synthetic KMS deployment-evidence staging and control-attestation workflow for the AWS KMS Tokyo and Google Cloud HSM Tokyo candidates. Verify actual-control evidence structure for region, HSM backing, non-exportable symmetric KEK, plaintext-KEK non-exposure, audit logging, rotation/old-version decrypt retention, IAM/admin/restore separation, deletion protection, residency, and private-network restriction; emit only redacted non-secret control attestations. Do not connect real cloud accounts, credentials, projects, keys, KMS APIs, or select a production vendor without explicit user authorization.
