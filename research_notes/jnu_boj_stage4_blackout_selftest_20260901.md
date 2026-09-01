# BOJ MPM Stage-4 new-entry blackout G1 selftest — 2026-09-01

- Candidate: BOJ_MPM_STAGE4_NEW_ENTRY_BLACKOUT_G1
- Preregistration commit: 113272f03429cc393f1cb2fdaaec43e18cd262e3
- Workflow run: 33501154606
- Artifact: 9797734168
- Result: **STAGE4_IMPLEMENTATION_SELFTEST_PASS**
- Cases: **15/15**
- Price/PnL outcomes used: **false**
- Formal Stage-5 independent replay: **not passed / pending**
- Alpha or risk-utility evidence: **none**
- Live use: **prohibited**

The first implementation correctly reproduced the frozen causal mapping, including pass-through outside blackout, exposure-increase suppression, risk-reducing exits, reversal-to-flat, release+20m end, missing-release fail-safe, cancellation of outstanding exposure-increasing orders at 11:00, and protection against treating 08:50 Summary/Minutes timestamps as policy-decision releases.

This result is Stage-4 implementation QA only. It cannot be interpreted as economic risk reduction, alpha, or a validated JNU module.
