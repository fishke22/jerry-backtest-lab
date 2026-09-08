# JNU Private KMS Deployment Evidence Staging Seal — 2026-09-08

Status: **CI PASS / SYNTHETIC KMS CONTROL ATTESTATION READY / REAL KMS BLOCKED**

## Core verification

- Core commit: `9b3e12fe2a1b9e241370a2184c25c49d6932947f`
- Integrity run: `34222961071` — PASS
- Actionlint: `34222961092` — PASS
- New KMS deployment evidence selftest: **31/31 PASS**
- Core CI passed on the first attempt; no fix commit was required.
- Stable v1.9 framework SHA: `2e0be163baccd8c42065b088116e313f9e34c39745bbdf509553063d500b1c85`

## Boundary established

The pipeline now supports synthetic repo-external deployment-control evidence for both `AWS_KMS_TOKYO` and `GCP_CLOUD_HSM_TOKYO`.

Vendor capability documentation is explicitly non-promoting. A deployment control can count only when backed by synthetic `INTERNAL_DEPLOYMENT_ATTESTATION` evidence under `INTERNAL_CONTROL_OWNER`. This prevents a public vendor feature page from being treated as proof that a specific JNU deployment has actually enabled the control.

Seventeen controls are covered: control class, vendor, Tokyo region, HSM backing, FIPS level >=3, non-exportable symmetric KEK, plaintext-KEK non-exposure, audit logging, rotation, previous-version decrypt retention, IAM separation, key-admin separation, restore-approver separation, delayed destruction/deletion protection, explicit residency configuration, and private-network restriction.

The emitter re-verifies source SHA-256 and emits no source paths, source text, account/project/key/resource identifiers, credentials, or key material. A complete synthetic control attestation still does not select a KMS vendor, modify the production key profile, enable production, create a key, call a KMS API, or authorize real activation.

## Regression state

All prior regressions remain PASS. Public real ledger remains **0 forecasts / 0 outcomes** and real entitlement remains **not connected**.

## Next stage

`PRIVATE_COMPOSITE_PRODUCTION_READINESS_EVIDENCE_JOIN_GATE_SYNTHETIC_ONLY`

Build a synthetic repo-external composite pre-activation evidence gate that joins a redacted provider/OSE term attestation with a redacted KMS deployment-control attestation, verifies shortlist identity and evidence lineage, evaluates all six market-data-provider × KMS candidate combinations without ranking or selecting them, and emits only blocker/readiness dossiers. Do not connect real provider/KMS accounts, ingest real confidential documents, select any vendor pair, create keys, connect credentials, or generate a real activation manifest without explicit user authorization.
