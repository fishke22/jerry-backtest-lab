# JNU Composite Evidence Dual-Control Review Seal — 2026-09-08

Status: **CI PASS / SYNTHETIC DUAL-CONTROL READY / REAL SELECTION AND ACTIVATION BLOCKED**

## Verification

- Core commit: `0b683a2dbb89c5ee0b8cc9182361363469ee5fd2`
- Integrity run: `34223789604` — PASS
- Actionlint: `34223789593` — PASS
- New dual-control selftest: **41/41 PASS**
- Core CI passed on the first attempt; no fix commit was required.
- Stable v1.9 framework SHA: `2e0be163baccd8c42065b088116e313f9e34c39745bbdf509553063d500b1c85`

## Governance added

All six composite pre-activation dossiers now require exactly two independent reviews:

- `EVIDENCE_REVIEWER`
- `CONTROL_REVIEWER`

The two reviewers must have different reviewer IDs. Each review is bound to the full composite dossier file SHA-256 and the canonical SHA-256 of the individual combination dossier.

Allowed dispositions are `APPROVE`, `REJECT`, and `NEEDS_EVIDENCE`. Disagreement is a fail-closed conflict. Two approvals still produce only `SYNTHETIC_DUAL_CONTROL_APPROVED_NOT_ACTIVATABLE`, and only if the underlying synthetic evidence dossier is complete.

Review timestamps enforce revalidation due dates and expiry. Stale or expired reviews become `SYNTHETIC_DUAL_CONTROL_REVALIDATION_REQUIRED`.

Replay protection is backed by the existing repo-external immutable-write/backup semantics. An exact replay of a review batch is idempotent; the same `review_batch_id` with different receipt content is rejected.

The receipt redacts reviewer IDs and retains only SHA-256 reviewer references. It emits no ranking, recommendation, selection, source text/path, credentials, cloud identifiers, key material, or real activation authorization.

Public real ledger remains **0 forecasts / 0 outcomes**. Market-data provider and KMS provider remain **UNSELECTED**.

## Next stage

`PRIVATE_VENDOR_PAIR_SELECTION_AUTHORIZATION_DECISION_GATE_SYNTHETIC_ONLY`

Build a repo-external synthetic vendor-pair selection authorization and decision-record gate that consumes a valid non-expired dual-control review receipt, verifies receipt/dossier lineage and six-pair coverage, and requires an explicit separate user-authorization artifact before any candidate pair could ever transition from UNSELECTED. In this stage, authorization must remain synthetic/disabled and no selection may be written. Test missing/expired/conflicting authorization, unauthorized pair substitution, replay, receipt tamper, and production-state mutation fail-closed. Do not select a real market-data provider or KMS vendor, contact providers, connect credentials/accounts, create keys, mutate production profiles, or generate a real activation manifest without explicit user authorization.
