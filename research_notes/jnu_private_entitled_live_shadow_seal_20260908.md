# JNU Private Entitled Live-Shadow Seal — 2026-09-08

Core commit:
`f36ec8bc885ae5743b747b295b2b6d793eabf2d8`

Stable v1.9 framework SHA:
`d16c3fcf3216d2e7a994bb32ec0860a1cfe7dc15f204f343a17a1e8108ab3324`

Cloud verification:
- Integrity `34173622041`: PASS.
- Actionlint `34173622030`: PASS.
- Private entitled live-shadow full chain: **16/16 PASS**.
- Private quote bridge: 10/10 PASS.
- Entitled quote evidence: 13/13 PASS.
- Private storage boundary: 9/9 PASS.
- Public boundary: 8/8 PASS.
- Public artifact safety: 4/4 PASS.
- V1.9 supersession: 17/17 PASS.
- Existing public v1.8 chain: PASS.
- Public real ledger remains 0 forecasts / 0 outcomes.

The private chain covers prepared request -> private quote receipt -> private forecast -> private outcome -> private scorer. Forecast tampering is rejected. Stdout redacts quote/decision/outcome/performance fields. No real entitlement is connected.
