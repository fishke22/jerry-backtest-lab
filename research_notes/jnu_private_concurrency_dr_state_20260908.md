# JNU Private Concurrency / DR / Launch-State Architecture — 2026-09-08

This stage adds lease-based cross-process locks, stale-lock quarantine through explicit recovery, deterministic concurrent launch handling, a monotonic private launch-state machine, portable private backup sets with per-file SHA-256 manifests, and disaster-recovery import with full recovery/scorer revalidation.

Backup-set encryption is intentionally not invented in this stage. Real entitled backup export remains prohibited until private encryption/key-management and OSE/provider retention/backup terms are explicitly resolved. Synthetic backup-set export/import is allowed for CI only.

No real entitlement data is connected and no public output is created.
