# JNU Private Concurrency / DR / State-Machine Seal — 2026-09-08

Core: `560e9019a3bef113fb5a59d1438d29407c1edb05`
Lock hierarchy correction: `1a0b1e56b6337453c007132740a9ef614d89835d`
Retention syntax correction: `3da3876c0fade6bbf61913231c255c7a7fb1f6f4`
DR state fixture correction: `b84bf573540d3db91ad651b9d0684d17135a6bde`

Final cloud verification:
- Integrity `34202481036`: PASS.
- Actionlint `34202144782`: PASS.
- New concurrency/DR/state selftest: **18/18 PASS**.
- Previous lifecycle regression: 19/19 PASS.
- Stable v1.9 framework SHA: `7f8ce80aef0a3e776f4faeaf11c58e53dd30f60c46c691402ac4fe88816ddb46`.
- Public real ledger: 0 forecasts / 0 outcomes.

The backup set deliberately excludes scorer results and launch-state cache. Results are recomputed and state is reconstructed after restore. Real backup export remains prohibited until encryption/key management and OSE/provider backup terms are resolved.
