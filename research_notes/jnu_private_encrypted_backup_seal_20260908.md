# JNU Private Encrypted Backup / Key Rotation / DR Drill Seal — 2026-09-08

Final synthetic envelope verification:
- Integrity run `34205335207`: PASS.
- Actionlint `34204715568`: PASS.
- Encrypted backup/key rotation/DR drill selftest: **28/28 PASS**.
- Stable v1.9 framework SHA: `dec203b8e92511cf1bacc69606a9acf0d194aa2214ad6f0b786e2bc0da1dd2e7`.
- Public real ledger remains 0 forecasts / 0 outcomes.

The implementation is true AES-256-GCM envelope encryption: an external private KEK wraps a fresh random per-backup DEK; payload files use the DEK with unique nonces and authenticated metadata; the manifest is authenticated by the DEK. Keyring metadata contains no key material; raw KEKs are separate external private 0600 files.

Restore authorization is bound to backup-set, key ID/version, exact destination, validity window, purpose, and single-use. Wrong key, ciphertext tamper, manifest tamper, expired authorization, key-version mismatch and non-single-use authorization are all rejected.

Real entitled backup remains prohibited until production KMS/HSM/key custody and OSE/provider backup-retention/cloud-processing terms are resolved.
