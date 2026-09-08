# JNU Private Concurrency Lock-Hierarchy Correction — 2026-09-08

The first DR selftest exposed a lock-hierarchy bug: backup export acquired an active export lock and then recovery scan correctly refused to operate while any active lock existed.

Correction:
- introduce a shared exclusive `ledger-mutation` lock for immutable forecast/outcome writes, recovery apply, retention apply, and backup export;
- recovery scan can ignore only the owner token of the operation that currently owns the global mutation lock;
- backup sets now contain authoritative immutable forecasts, outcomes, and their recovery backups only;
- scorer results are recomputed after DR import;
- launch state is reconstructed after DR import instead of snapshotted.

No market-data, directional, freshness, entitlement, or publication rule changed.
