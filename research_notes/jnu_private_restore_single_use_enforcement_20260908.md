# JNU Encrypted Restore Single-Use Enforcement — 2026-09-08

A successful encrypted restore now consumes its restore authorization in a repository-external private usage registry. Reusing the same restore_id is rejected even if the previous restore destination has been deleted.

Failed restore attempts do not consume authorization. The usage registry is protected by a cross-process private lock.

This closes the gap between the protocol's single-use requirement and executable behavior. No directional, market-data, 900-second, entitlement, or public-output rule changed.
