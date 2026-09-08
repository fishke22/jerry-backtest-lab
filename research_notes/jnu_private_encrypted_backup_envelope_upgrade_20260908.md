# JNU Encrypted Backup Envelope Upgrade — 2026-09-08

A parallel synthetic encrypted-backup implementation landed before this stage was sealed. Its CI passed, but review found that it used the KEK directly for every payload file, lacked time-bounded/single-use restore authorization, and retained plaintext SHA-256 values in the private manifest.

This upgrade preserves the existing file names and replaces the crypto internals with a true AES-256-GCM envelope:
- external private KEK metadata is separated from raw key material files;
- a fresh random 256-bit DEK is generated per backup-set;
- the active KEK wraps only the DEK;
- each payload file is encrypted under the DEK with a unique nonce and authenticated AAD;
- the backup manifest is itself authenticated by the DEK;
- manifest contains key ID/version but no key bytes and no plaintext hashes;
- restore authorization binds backup-set, key ID, key version, destination, validity window, purpose, and single-use flag.

Real entitled backup export remains prohibited.
