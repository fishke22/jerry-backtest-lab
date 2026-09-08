# JNU Private KMS Deployment Evidence Staging / Control Attestation

Stage: \`PRIVATE_KMS_DEPLOYMENT_EVIDENCE_STAGING_CONTROL_ATTESTATION_PIPELINE_SYNTHETIC_ONLY\`

This stage separates **vendor capability evidence** from **actual deployment-control evidence**.

Vendor documentation may establish that a service can support an HSM, rotation, logging, or a Tokyo region. It does not prove that the JNU deployment is configured that way. A deployment control is promotable only when the evidence source role is \`DEPLOYMENT_CONTROL\`, source class is \`INTERNAL_DEPLOYMENT_ATTESTATION\`, and authority is \`INTERNAL_CONTROL_OWNER\`.

The synthetic pipeline covers AWS KMS Tokyo and Google Cloud HSM Tokyo. It requires control evidence for control class, candidate vendor/region, HSM backing, FIPS level >=3, non-exportable symmetric KEK, plaintext-KEK non-exposure, audit logging, rotation and old-version decrypt retention, IAM separation, key-admin separation, restore-approver separation, delayed destruction/deletion protection, explicit residency configuration, and private-network restriction.

All source documents, intake metadata, stage records, and redacted outputs remain outside the public repository. The emitter re-verifies each source SHA-256 before use and removes source paths, source text, credentials, account/project/key/resource identifiers, and any production authorization.

Even a complete synthetic control attestation does not select AWS or Google Cloud, does not modify the current production key profile, and does not authorize a real backup.
