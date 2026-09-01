# BOJ MPM Stage-5 Nautilus independent execution replay G1

- Status: **PASS_STAGE5_INDEPENDENT_EXECUTION_REPLAY**
- Scenarios: **12/12**
- Engine: NautilusTrader 1.231.0
- Real JNU prices used: **false**
- PnL/alpha/utility evaluated: **false**
- Live use: **false**

| Scenario | PASS | Fills exp/actual | Position exp/actual | Canceled |
|---|---:|---:|---:|---:|
| NON_MPM_PASSTHROUGH | True | 1/1 | 1/1 | 0 |
| MPM_BEFORE_1100_PASSTHROUGH | True | 1/1 | 1/1 | 0 |
| MPM_AT_1100_ENTRY_SUPPRESSED | True | 0/0 | 0/0 | 0 |
| MPM_EXIT_INSIDE_BLACKOUT | True | 2/2 | 0/0 | 0 |
| MPM_EXPOSURE_INCREASE_SUPPRESSED | True | 1/1 | 1/1 | 0 |
| MPM_REVERSAL_CLAMP_TO_FLAT | True | 2/2 | 0/0 | 0 |
| RELEASE_PLUS_19M_BLOCKED | True | 0/0 | 0/0 | 0 |
| RELEASE_PLUS_20M_UNBLOCKED | True | 1/1 | 1/1 | 0 |
| MISSING_RELEASE_FAILSAFE | True | 0/0 | 0/0 | 0 |
| SUMMARY_0850_NOT_POLICY_RELEASE | True | 0/0 | 0/0 | 0 |
| UNSCHEDULED_OUT_OF_SCOPE | True | 1/1 | 1/1 | 0 |
| OUTSTANDING_ENTRY_CANCEL_AT_1100 | True | 0/0 | 0/0 | 1 |

Stage-5 PASS, if achieved, is execution/mechanical validation only and is not evidence of alpha or economic risk reduction.
