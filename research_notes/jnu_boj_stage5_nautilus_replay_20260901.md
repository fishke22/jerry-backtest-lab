# BOJ MPM Stage-5 Nautilus independent replay — 2026-09-01

## Result
- Candidate: BOJ_MPM_STAGE5_NAUTILUS_EXECUTION_REPLAY_G1
- Eligible run: 33502066320
- Artifact: 9798096673
- Status: **PASS_STAGE5_INDEPENDENT_EXECUTION_REPLAY**
- Preregistered scenarios: **12/12 PASS**
- Engine: NautilusTrader 1.231.0
- Independent code path: true
- Imports Stage-4 selftest: false
- Real JNU price data: false
- Real PnL: false
- Alpha / economic risk-utility evidence: none
- Live use: prohibited

The replay independently reproduces passthrough, blackout suppression, risk-reducing exit, exposure-increase suppression, reversal-to-flat, release+19/+20 boundary, missing-release fail-safe, Summary/Minutes isolation, unscheduled-event exclusion, and cancellation of a resting exposure-increasing limit order at 11:00.

The earlier run 33501798114 is engineering-ineligible: Nautilus 1.231.0 required the Order object in cancel_order. ENG1 changed only that API call; no research rule or scenario changed.

## Interpretation
Stage 5 confirms mechanical execution consistency only. BOJ G1 remains an event-risk overlay, not directional alpha and not a validated live module. Stage 6/7 economic validation is blocked until a validated base-entry process exists and an evaluation protocol is frozen without post-hoc parameter search.
