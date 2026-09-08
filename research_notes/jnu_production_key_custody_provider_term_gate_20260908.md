# JNU Production Key Custody / Provider-Term Readiness Gate — 2026-09-08

This stage does not connect a real KMS/HSM and does not enable real entitled backups.

Production key custody is constrained to a control class rather than a vendor:
- preferred: managed HSM-backed KMS with non-exportable KEK and envelope encryption;
- escalation: dedicated/customer-controlled HSM/custom key store only if contract or internal policy requires it;
- prohibited: synthetic file keyring, plaintext/exportable software KEK, environment-variable KEK, GitHub Actions secret KEK, or shared human credentials.

Current official cloud documentation supports the control-class decision:
- AWS KMS standard key stores protect key material in FIPS 140-3 Level 3 HSMs, do not export KMS key material in plaintext, support customer-managed symmetric rotation, and log KMS API operations through CloudTrail.
- Google Cloud HSM exposes HSM-backed keys through Cloud KMS using Level-3-certified HSMs and supports key rotation.

OSE market-information policy separately requires approval for Service Facilitators using Information for consigned system operations. Therefore technical KMS compliance alone cannot authorize real OSE data processing.

The provider-term gate requires explicit approvals/confirmations for entitlement, applicant/product/provider, read-only transport, OSE and provider cloud processing, Service Facilitator status, encrypted backup creation/storage/region, retention/deletion, restore, DR drills, KMS/HSM custody, incident reporting, and audit cooperation.

Current manifests remain intentionally UNRESOLVED/BLOCKED.
