# JNU Vendor-Pair Authorization Lifecycle Audit-Chain Seal — 2026-09-08

Status: **CI PASS / APPEND-ONLY SYNTHETIC AUTHORIZATION LIFECYCLE / NO SELECTION**

## Verification

- Core commit: `18a7c20b3ac4cac877fafa2415acaf8621d01e83`
- Integrity run: `34225172423` — PASS
- Actionlint: `34225172485` — PASS
- New lifecycle selftest: **40/40 PASS**
- Core CI passed on the first attempt; no fix commit was required.
- Stable v1.9 framework SHA: `2e0be163baccd8c42065b088116e313f9e34c39745bbdf509553063d500b1c85`

## Lifecycle governance now enforced

Vendor-pair authorization now has an append-only repo-external lifecycle with immutable `ISSUE`, `SUPERSEDE`, and `REVOKE` events. Every event has a contiguous sequence and parent-event SHA-256. Current authorization is derived by verifying and replaying the complete chain; there is no mutable current pointer.

`ISSUE` requires no active authorization. `SUPERSEDE` must target the current authorization and may not silently change the vendor pair. A pair change requires an explicit `REVOKE` followed by a new `ISSUE`. `REVOKE` requires the current target, an explicit reason, user-principal role, and explicit synthetic revocation attestation.

Superseded, revoked, and expired authorizations are not usable as current authorization.

Exact event replay is idempotent. Reusing an event ID with different request content is rejected. The audit chain detects event-file tamper, missing sequence numbers, broken parent SHA lineage, and backward timestamps.

All authorization artifacts remain `SYNTHETIC_DISABLED`, with selection writes prohibited and real selection unauthorized.

Public real ledger remains **0 forecasts / 0 outcomes**. Provider and KMS selections remain **UNSELECTED**.

## Next stage

`PRIVATE_SELECTION_DECISION_LIFECYCLE_CURRENT_AUTHORIZATION_INTEGRATION_GATE_SYNTHETIC_ONLY`

Integrate the repo-external authorization lifecycle audit chain into the synthetic vendor-pair selection decision gate. Require the decision request's authorization ID and SHA-256 to be the usable current authorization derived from the fully verified ISSUE/SUPERSEDE/REVOKE chain at decision time, and fail closed on revoked, superseded, expired, tampered, missing, or forked lifecycle state. Preserve exact receipt/pair bindings, immutable decision replay, and production-state checks. Keep authorization disabled, selection writes prohibited, providers/KMS UNSELECTED, production profiles unchanged, and real activation prohibited.
