# JNU Shadow Transaction Fault-Injection / Rollback Seal — 2026-09-09

Status: **CI PASS / SHADOW ATOMICITY + ROLLBACK VERIFIED / PRODUCTION UNCHANGED**

## Verification

- Core commit: `4bf025cbfeca1ff2b5d0f16754a9013a86ef6faa`
- Integrity run: `34321924756` — PASS
- Actionlint: `34321924830` — PASS
- New shadow fault-injection selftest: **46/46 PASS**
- NOOP executor regression: **39/39 PASS**
- Commit-authorization regression: **44/44 PASS**
- PREPARE review regression: **47/47 PASS**
- PREPARE regression: **40/40 PASS**
- Lifecycle-integrated selection regression: **34/34 PASS**
- Selection-authorization regression: **53/53 PASS**
- Authorization-lifecycle regression: **40/40 PASS**
- Core CI passed on the first attempt; no fix commit was required.
- Stable v1.9 framework SHA: `2e0be163baccd8c42065b088116e313f9e34c39745bbdf509553063d500b1c85`

## Shadow transaction mechanics validated

The frozen seven-step transaction sequence now executes against repo-external disposable shadow copies only.

Real shadow-side lock acquisition, CAS verification, checksum-backed preimage backup, synthetic mutation, post-write verification, rollback and immutable receipt generation were exercised.

Deterministic fault injection covers every transaction step. Mutation faults occur after the first shadow write. Rollback faults simulate an interruption after the first restore and then resume. Final-receipt faults force rollback before receipt retry.

Stale shadow CAS blocks before backup. Corrupted preimage backup blocks before mutation. Every rollback path restores all three shadow files byte-for-byte and SHA-256-for-SHA-256.

The authoritative shortlist, production key profile and provider-term state remained byte-for-byte unchanged across all tests. No production lock or production backup was created.

Public real ledger remains **0 forecasts / 0 outcomes**. Provider/KMS remain **UNSELECTED**.

## Next stage

`PRIVATE_SELECTION_TRANSACTION_SHADOW_CRASH_RECOVERY_JOURNAL_REPLAY_SYNTHETIC_ONLY`

Build a repo-external synthetic crash-recovery journal and replay layer over the disposable shadow transaction simulator. Persist an append-only step journal before/after each shadow transaction phase, simulate process crash at every boundary, and on recovery deterministically decide whether to resume forward, rollback from checksum-verified preimages, or finalize an already-complete transaction. Enforce one transaction ID/one lineage, monotonic journal sequence, parent-hash chaining, exactly-once final receipt semantics, stale-lock recovery rules, and replay/tamper detection. Prove every crash-recovery path leaves either a fully verified shadow-success state or an exact preimage-restored state, while authoritative production files remain byte-for-byte unchanged. Keep authorization disabled and expose no real COMMIT/APPLY capability.
