# JNU Provider Evidence Intake / Contact Questionnaire Pack — 2026-09-08

Status: DRAFT / UNSENT / NO PROVIDER SELECTED / NO CREDENTIALS

This pack implements the current JNU next action without contacting any external party. It is a question-and-evidence checklist only. Completing a questionnaire does not constitute contract permission, entitlement approval, vendor selection, or production activation. Confidential documents must stay outside the public repository; only hashes, locators, status values, and reviewer attestations may later enter the public governance record.

## Common non-negotiable boundary

- Exact OSE Nikkei 225 Micro individual contract month is required; continuous substitutes are not acceptable.
- Provider timestamps remain subject to the frozen <=900 second rule.
- Data-only/read-only access must be separable from broker authentication and trading permission.
- No API key, token, password, private key, or other secret may be placed in this repository or questionnaire artifact.
- Private third-party cloud processing, encrypted backup, retention, deletion, restore, DR drill, incident, and audit terms must be explicit; no permission may be inferred from technical capability.
- Public raw or derived entitled output remains prohibited unless separately authorized.
- No outreach is authorized by this document.

## Market-data provider questionnaire — Broadridge / CQG

Current shortlist status: Tier A technical transport evidence partial.

1. Confirm realtime OSE Nikkei 225 Micro Futures for an exact individual contract month, including instrument identity and provider timestamp semantics.
2. Confirm whether a data-only read-only session can be provisioned with no ability to place/amend/cancel orders and no broker-auth requirement.
3. Confirm technical and permission separation between read-only market-data transport and any order-capable CQG transport.
4. Confirm whether the OSE Free Trial, if applicable, can be delivered through this path and what eligibility/provider steps apply.
5. State whether private third-party cloud processing by the entitled subscriber is permitted.
6. State whether encrypted private backups may be created and stored, including acceptable regions.
7. State retention and deletion/destruction terms for encrypted backups.
8. State whether restore and periodic private DR drills are permitted.
9. State whether managed HSM-backed KMS envelope encryption is acceptable or subject to restrictions.
10. State incident-reporting and audit/cooperation obligations.

Requested evidence form: explicit written confirmation, contract/policy locator, and source-document hash/locator suitable for the term-evidence attestation protocol.

## Market-data provider questionnaire — QUICK Corp.

Current shortlist status: Tier B OSE provider only.

Use the same ten questions above, with two additional confirmations:

- Identify the programmatic realtime transport/API suitable for this exact use case.
- Confirm exact individual-month Nikkei 225 Micro identity and provider timestamp semantics on that transport.

## Market-data provider questionnaire — Refinitiv / LSEG

Current shortlist status: Tier B OSE provider only.

Use the same ten questions above, with two additional confirmations:

- Identify the programmatic realtime transport/API suitable for this exact use case.
- Confirm exact individual-month Nikkei 225 Micro identity and provider timestamp semantics on that transport.

## OSE authority questionnaire

Request explicit OSE confirmation for each field below:

1. Entitlement path applicable to the proposed read-only exact-Micro use case.
2. Applicant eligibility.
3. Exact individual-contract-month Nikkei 225 Micro coverage.
4. Permission for private third-party cloud processing by the entitled subscriber.
5. Whether a service facilitator/provider is required and, if so, its approval/registration requirement.
6. Permission to create and store private encrypted backups.
7. Region/residency restrictions on backup and DR processing.
8. Retention limits.
9. Deletion/destruction duties, including end-of-entitlement handling.
10. Restore permission.
11. Periodic private DR-drill permission.
12. Requirements/restrictions on managed HSM-backed KMS key custody.
13. Incident-reporting obligations.
14. Audit/cooperation obligations.

## AWS KMS Tokyo deployment-profile attestation — internal control owner

Candidate: AWS_KMS_TOKYO; proposed region ap-northeast-1.

Do not mark production-ready from public documentation alone. The deployment owner must attest the actual configured profile for:

- managed HSM-backed KMS control class and exact region;
- HSM-backed/non-exportable symmetric KEK behavior;
- application never receiving plaintext KEK;
- audit logging enabled;
- key rotation enabled and prior decrypt versions retained as required;
- IAM role separation;
- key-admin vs crypto-user separation;
- restore-approver vs crypto-user separation;
- deletion protection or delayed destruction;
- explicit region/residency configuration;
- private network path or equivalent restriction.

Every production assertion needs an evidence ID and reviewer attestation.

## Google Cloud HSM Tokyo deployment-profile attestation — internal control owner

Candidate: GCP_CLOUD_HSM_TOKYO; proposed region asia-northeast1.

Apply the same deployment-attestation fields as AWS. Public vendor documentation is only a baseline. Actual project/key-ring/key/IAM/logging/network/deletion configuration must be separately attested before the production key profile can change from UNSELECTED_BLOCKED.

## Intake handling

Future external responses, contracts, or written confirmations must be staged outside the public repository. The public attestation layer may retain only non-secret metadata permitted by config/jnu_term_evidence_attestation_protocol_v1.json: source class/authority, URI or external path locator, document SHA-256, capture time, confidentiality label, field-level claim value, locator, explicitness, and reviewer attestation.

No message in this pack has been sent.
