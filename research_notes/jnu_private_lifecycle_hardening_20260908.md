# JNU Private Lifecycle Hardening — 2026-09-08

This stage adds deterministic one-request/one-private-forecast idempotency, exact outcome replay protection, atomic fsync/rename writes, private backups with SHA-256 sidecars, recovery, scorer checkpoints, and synthetic retention quarantine.

Permanent deletion remains prohibited until real OSE/provider retention obligations are explicitly confirmed. Retention tooling in this stage is synthetic-only and quarantines completed forecast/outcome pairs rather than purging them.

No real entitled data is connected and no public output is introduced.
