# JNU v1.9 Framework Hash Self-Reference Correction — 2026-09-08

The authoritative framework must not contain its own content hash. Embedding its current SHA inside itself changes the content and therefore changes the SHA recursively.

Correction:
- remove `source_governance.runtime_framework_sha256` from v1.9;
- retain framework hashes only in external checkpoints/memory;
- runtime preflight/registrar/scorer continue computing the framework SHA directly from the current file.

No directional/scoring/source gate changes.
