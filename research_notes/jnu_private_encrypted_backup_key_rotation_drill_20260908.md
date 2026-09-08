# JNU Private Encrypted Backup / Key Rotation / DR Drill — 2026-09-08

This stage adds a repo-external private keyring and synthetic AES-256-GCM backup encryption. Key material is never committed, never stored in the encrypted backup manifest, and never printed.

Each payload file uses an independent 96-bit nonce. AES-GCM AAD binds backupset ID, relative path, authoritative framework SHA, key ID, and key version. Wrong-key use and ciphertext tampering must fail authentication.

Key rotation preserves retired keys so old backup generations remain restorable. Backup rotation quarantines old generations rather than deleting them. Restore requires an explicit synthetic restore-authorization manifest. DR drills write private reports with measured RTO and backup age; no raw market data or key material is emitted.

Real entitled encrypted backup export remains prohibited until OSE/provider backup terms and production key custody/KMS governance are explicitly resolved.
