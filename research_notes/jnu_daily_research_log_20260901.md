# JNU Daily Research Log — 2026-09-01

## MACD(4,22,3) post-publication True-OSE Mini Stage A
- Canonical family: MACD_4_22_3_POSTPUBLICATION_TRUE_JNU_G1
- Pre-outcome DI1 corrected session-end handling so 15:15 is the Stage-A final minute; no research-spec change.
- Authorized local 225Labo Mini raw used read-only from D:\QROS\data\personal_licensed\225labo\mini\raw.
- Gate 0: 251 evaluation days, 0 excluded, 0 duplicate minute rows, 0 invalid rows, 0 critical DQ.
- Derived panel SHA-256: 0ec1eee844d04c393d0576c831dc82fdec86a191b04ccd1618d344302a7f9be7.
- Derived panel/manifest cloud commit: bd444897bbe0ee0d1b47daca4b4e2291ab9cb547.
- Formal GitHub Actions run: 33498323765; artifact: 9796634718.
- Result: TRUE_OSE_MINI_STAGE_A_FAIL_TERMINAL.
- Mean gross daily strategy return: -3.0451509658307074e-05.
- Directional accuracy: 0.492.
- 5-day moving-block bootstrap P(mean>0): 0.5504.
- Disposition: exact-JNU Micro Stage B prohibited; no MACD retuning/filter/execution/sample rescue.
- Decision engine remains NO_VALIDATED_DIRECTIONAL_EDGE.
- HAR-RSV and BOJ MPM remain Stage-3 risk-information candidates only.
- Directional checkpoint: five recent independent/literature-grounded directional families failed strict true-target gates; pause close-variant search.

## Independent directional scout + Stage-4 priority
- No new formal directional family opened.
- BOJ MPM DI3 corrected three official decision timestamps; exact-JNU Stage B reconfirmed PASS on 25 events, run 33499625359.
- Stage-4 priority #1: BOJ MPM new-entry blackout design (pre-prereg only); #2 HAR-RSV exposure-cap design.
- Top independent directional mechanism found: U.S. option-implied left-tail risk to Japanese returns; currently data-rights/free-history blocked.
- CFTC Nikkei positioning remains scouting-only because direct predictive literature is insufficient.

## BOJ MPM Stage-4 new-entry blackout G1 engineering selftest
- Preregistration was committed before outcome-free engineering replay: 113272f03429cc393f1cb2fdaaec43e18cd262e3.
- GitHub Actions run: 33501154606; artifact: 9797734168.
- Result: STAGE4_IMPLEMENTATION_SELFTEST_PASS, 15/15 cases.
- No JNU price/PnL outcomes were used; this is implementation QA only.
- Formal Stage-5 independent replay has NOT passed and remains pending.
- No alpha/utility evidence; live use remains prohibited.

## BOJ MPM Stage-5 independent Nautilus replay
- First cloud run 33501798114 is permanently classified INELIGIBLE_ENGINEERING_RUN due solely to Nautilus cancel_order API object-type mismatch before full classification; research spec/scenarios were unchanged.
- Eligible replay run: 33502066320; artifact: 9798096673; head: 3b0d5ea9152e1ec1f83b3b9a85de24ae69de3a0e.
- Result: PASS_STAGE5_INDEPENDENT_EXECUTION_REPLAY, 12/12 preregistered scenarios.
- Real JNU prices/PnL used: false. Alpha/utility evidence: none. Live use: prohibited.
- BOJ G1 is frozen at Stage-5 ceiling until a validated base-entry process exists.

## Tail-risk continuation search
- Public author LJV enables historical replication through 2017; Japanese paper sample reaches 2018-06.
- Later research demonstrates comparable LJV calculation through 2021, but no rights-clean self-service post-2021 U.S. LJV series was verified.
- JPX Japanese LJV through 2024-03 is not a valid substitute for U.S. LJV.
- No new directional family opened.

## PCR parser regression and first cloud smoke
- Frozen 9-date regression after modern YYYYMM MM.DD prefix fix: 9/9 PASS; no directional returns used.
- Cloud smoke 33509640334 is mixed, not a directional/research FAIL. 2016-01 was an engineering parser defect; 2026-08 exposed valid zero-call-denominator days on 2026-08-26 and 2026-08-31.
- Frozen zero-denominator rule remains unchanged; no strike/day/formula rescue.

## PCR second cloud smoke evidence audit
- Run 33512367293 completed SUCCESS but is engineering-ineligible after evidence audit: 2016-01-29 legacy no-trade second-near PUT was misread as 13,103,751,803.1 volume.
- Fixed structurally: ellipsis-only legacy trade fields => zero volume; YYYYMMDD weekly rows excluded before standard-month parsing.
- Frozen 9-date QA remains 9/9 PASS. Targeted 2016-01-29 and 2019-12-30 engineering regressions PASS.
- Local 2016-01 PCR-only smoke now yields monthly PCR 366.4021493956121; no return outcomes used.

## PCR third cloud smoke PASS and full-panel prereg
- Run 33513973356 / artifact 9802914506: PCR_CLOUD_SMOKE_PASS. 2016-01-29 daily PCR=69.71514242878561; 2016-01 monthly PCR=366.4021493956121.
- 2026-08 remains PCR_UNDEFINED_REQUIRED_DAY on 2026-08-26 and 2026-08-31 due to zero selected call denominator.
- Full information-only data gate frozen before execution: 0 parser/source errors; >=185 defined of 205 archive-complete months; >=30 defined in latest 36 archive-complete months.
- No directional returns inspected; no formal directional family opened.
