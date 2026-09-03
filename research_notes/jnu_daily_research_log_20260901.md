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

## PCR full-panel first-run engineering recovery
- Full-panel run 33514784926 at head 8cbd4b4 is DATA_GATE_NOT_EVALUABLE_ENGINEERING_FAILURE, not a research/data transportability FAIL.
- 2014-2017 and 2018-2021 shards exposed a 2016-07 through 2019-11 OSE PDF text-order/layout transition; directional returns remained unread.
- Recovery preserves PCR definition, frozen QA dates, source manifest and all preregistered Gate thresholds.
- Frozen 9-date regression: 9/9 unchanged under pypdf 6.0.0. Transition-layout smoke: 20/20 required days across 2016-07, 2017-06, 2018-01, 2019-11; 4/4 months PCR_DEFINED.
- 2016-07-25 selected-leg audit: 201608 PUT 904+1399, CALL 63+2; 201609 PUT 8+1605, CALL 17+0 (Auction+J-NET).
- No raw NDL/JPX report uploaded. Next: commit/push recovery and dispatch the same preregistered full-information-panel workflow.

## PCR full-panel recovery run checkpoint
- Invalid run 33514784926 was cancelled after engineering invalidation to stop redundant source downloads; it remains DATA_GATE_NOT_EVALUABLE_ENGINEERING_FAILURE.
- Active recovery run 33520336720 at c65ea6e: 2014-2017 shard SUCCESS, artifact 9805796894.
- 2014-2017: 48/48 PCR_DEFINED, 240/240 required days parsed, 0 parser/source errors, 0 noninteger/negative selected-volume fields, all 240 NDL provenance SHA present.
- Data Gate not evaluated; directional outcomes remain unread; formal directional family remains unopened.

### PCR recovery run 2018-2021 shard cloud verification
- Run 33520336720 shard 2018-2021: SUCCESS; artifact 9806942661.
- 47 PCR_DEFINED months, 1 PCR_UNDEFINED_REQUIRED_DAY month, 0 parser/source errors.
- The prior 23 transition-era parser failures are eliminated in the cloud run.
- 2018-12-25 is undefined only because both selected CALL legs have zero official volume (ZERO_SELECTED_CALL_DENOMINATOR); this is a frozen-definition data outcome, not an engineering failure.
- 240/240 required days have NDL provenance SHA; all selected volume fields are nonnegative integers; no directional outcomes inspected.

### PCR recovery cloud checkpoint: 2018-2021 shard
- Run 33520336720 2018-2021 shard SUCCESS; artifact 9806942661; 47 PCR_DEFINED + 1 PCR_UNDEFINED_REQUIRED_DAY; 0 parser/source errors.
- 2018-12-25 undefined reason is frozen ZERO_SELECTED_CALL_DENOMINATOR with both selected call legs explicitly zero-volume; no directional outcomes inspected.

### PCR recovery run 2009-2013 shard cloud verification
- Run 33520336720 shard 2009-2013: SUCCESS; artifact 9807745504.
- 52 PCR_DEFINED, 3 ARCHIVE_INCOMPLETE, 1 PCR_UNDEFINED_REQUIRED_DAY, 0 parser/source errors.
- Recovery panel JSON SHA256 exactly matches prior control: ffa00e69afd09932cf1487df2c59aa08f895781ab7d6a7ad69b94d0c068fbd80.
- Known archive gaps remain 2009-05, 2009-06, 2010-06; 2010-08-31 remains ZERO_SELECTED_CALL_DENOMINATOR.
- Directional outcomes remain unopened; Data Gate not yet evaluated.

## PCR full-panel recovery run 33520336720 final engineering disposition
- Run completed with 3 successful shards, 2022-2026 engineering failure, and a successful 208-month merge artifact 9809516285.
- Frozen Gate metrics met every threshold except zero parser/source errors: 196/205 defined, 95.61%, recent 30/36; exactly one parser-error month, 2023-02.
- Root cause: 2023-02-24 PDF removes whitespace in the reference label; official Nikkei reference close 27,453.48 is present. This is engineering, not missing data or research failure.
- Whitespace-only label normalization repairs 2023-02 to 5/5 days; frozen 9-date pre/post builder outputs match 9/9 exactly.
- Local repaired-shard assertion changed only 2023-02. Local full-panel preflight: 197/205 defined, 0 parser errors, recent 30/36, all frozen Gate checks PASS.
- Official Gate remains unevaluated until targeted cloud recovery produces an authoritative artifact; directional outcomes remain unopened.

## PCR full-information Data Gate authoritative PASS
- Targeted engineering recovery run 33611084116 at 786e236 completed SUCCESS; artifact 9839020223, digest f80304ff...0cb8d2.
- Recovery assertion changed only 2023-02 in the 2022-2026 shard; repaired shard SHA256 a00cc5ea...8aac.
- Full panel SHA256 d714c375...3332; independent audit SHA256 efc1a6c4...fd91.
- Frozen Gate PASS: 208 total, 205 archive-complete, 197 PCR_DEFINED, 8 undefined-required-day, 3 known archive gaps, 0 parser/source errors.
- Coverage: 197/205 = 96.10%; recent 36 = 30/36 = 83.33%; every frozen Gate check PASS.
- This is information/data feasibility only, not alpha evidence. Directional outcomes remain unopened and formal directional family remains closed.
- Next legal step: commit a separate post-publication directional preregistration before inspecting future Nikkei/JNU returns.

## PCR post-publication directional family terminal result (2026-09-02)
- Authoritative PCR information Data Gate remains PASS: 197/205 defined, 0 parser/source errors.
- Frozen published rule: PCR < 88.7 SHORT; PCR > 116.5 LONG; otherwise FLAT; signal month t applied only to month t+1.
- First valid directional outcome: PCR_POSTPUBLICATION_DIRECTIONAL_RULE_FAIL; 173 active months.
- Primary 10 bps cumulative +3.2554%, annualized Sharpe 0.09569; 20 bps stress -12.1318%; bootstrap 95% lower mean monthly return -0.56956%.
- Fixed subperiods positive: 1/4; recent 2023-01..2026-08 cumulative +94.8986% does not override failed robustness gates.
- Independent arithmetic audit: 1025/1025 row checks pass; primary/stress/Sharpe/bootstrap/subperiod outputs reproduce exactly.
- Governance disposition: TERMINAL_FAIL_NO_RESCUE. No threshold retuning, sample rescue, or reopening of this PCR family.

## News Language/Source G1 terminal data disposition sync (2026-09-02)
- Research branch research/news-language-source-g1 terminal HEAD: 87b04d491185cdce5b0901ba444298b94e671580.
- Final disposition: DATA_INCONCLUSIVE; logical attempts used 3/3; 311 required cache windows still missing.
- Statistical evaluation was not performed; directional trading remained prohibited by preregistration.
- No fourth acquisition attempt is allowed. This family is closed as data-inconclusive, not research FAIL.

## HAR-RSV Stage8 forward holdout prereg/selftest (2026-09-02)
- Stage8 prereg frozen before any post-2026-08-31 JNU outcome: first 126 new eligible Micro trading days only.
- Fail-closed selftest: 0/126 days available; 126 remaining.
- Partial QLIKE/MSE/bootstrap computation is prohibited and was not performed; holdout_metrics is absent from the result.
- Current status: STAGE8_FORWARD_HOLDOUT_PENDING_INSUFFICIENT_NEW_DATA.

## BOJ MPM Stage8 forward-event prereg/selftest (2026-09-02)
- Stage8 frozen before post-2026-07-31 event outcomes: first 8 new eligible BOJ decision events only.
- Fail-closed selftest: 0/8 new events available; 8 remaining.
- Partial event-effect mean/median/bootstrap is prohibited and was not computed; holdout_metrics is absent.
- Both pending Stage3 finalists now have Stage8 protocols frozen before future outcomes.

## Stage9 role-validation gate prereg/selftest (2026-09-02)
- Stage9 admission rules frozen before either Stage8 forward outcome.
- Selftest: HAR-RSV and BOJ event-state are both STAGE9_BLOCKED_STAGE8_PENDING.
- Validated JNU modules remain 0; validated directional modules remain 0; direction engine remains NO_VALIDATED_DIRECTIONAL_EDGE.
- PCR fixed-threshold terminal failure added to the permanent family attempt ledger; no rescue/reopen by parameter tuning.

## Stage8 cloud readiness gate validation (2026-09-02)
- Readiness-only workflow added at .github/workflows/jnu-stage8-readiness-v1.yml.
- Push run 33626204221 PASS; artifact 9844872997.
- Manual run 33626221824 PASS; artifact 9844882077.
- Both cloud runs match local semantics: HAR 0/126, BOJ 0/8, performance/effect columns not read and metrics not computed.

## Authoritative validation pipeline checkpoint (2026-09-02)
- Validation head: ff322f11dbb23da6be093056ac6ef47f2db10e4a.
- Stage8 readiness cloud run 33626955473 PASS; artifact 9845172659.
- Framework-status cloud run 33626897106 PASS; artifact 9845149864.
- Final-completion cloud audit run 33626831915 PASS; artifact 9845124762.
- Current state remains 6/8 major candidates terminal, HAR/BOJ Stage8 pending, validated JNU modules 0, directional modules 0.
- The only active research blocker is future untouched exact-JNU data accumulation; no partial Stage8 outcome inspection is permitted.

## Stage8 local forward-data ingest orchestrator (2026-09-02)
- Added scripts/ingest_jnu_stage8_forward_local.py; it performs no login/download and keeps licensed raw data local-only.
- Check-only selftest on current four Micro annual packages: NO_SOURCE_CHANGE; no derived modification.
- --apply selftest with unchanged source also no-op; tracked repo diff remained empty.
- Builder provenance is resolved from each builder last-touch Git commit; future annual packages are dynamically discovered.

## Authoritative JNU Operational Framework frozen (2026-09-02)
- Current operational framework persisted at config/jnu_operational_framework_current_v1.json.
- Future JNU/Osaka Nikkei analyses must use its nine-layer regime/event/cross-market/price-discovery/path/positioning/SQ/evidence-fusion/decision-output structure.
- HAR-RSV and BOJ remain role-constrained TRUE_JNU_CONFIRMED / FORWARD_VALIDATION_PENDING modules; no validated directional edge exists yet.
- Rejected PCR/MACD/USDJPY/overnight/simple US-to-JNU families remain prohibited as directional signals.

## JPX Nikkei 225 mini foreign-flow sign family terminal result (2026-09-02)
- Source/PIT Data Gate PASS: 554/554 parsed, 528 standard PIT weeks, 26 irregular weeks excluded under preregistered fail-closed rule.
- Phase1 observations: 527; long 239 / short 288 / flat 0.
- 10bps cumulative -71.7288%; 20bps cumulative -83.8472%; annualized Sharpe -0.48798.
- Moving-block bootstrap 95% lower mean weekly net -0.41472%; positive subperiods 0/4; recent 104 weeks -30.1084%.
- Independent arithmetic audit 3162/3162 row checks PASS; all aggregate checks reproduce exactly.
- Governance: TERMINAL_FAIL_NO_RESCUE. Do not test the opposite sign as a rescue of this family.

## JPX cash foreign-flow sibling terminal result (2026-09-02)
- Data Gate PASS: 554/554 parsed, 528 standard PIT weeks, 527 complete phase1 observations.
- 10bps cumulative -26.3243%; 20bps -50.0341%; Sharpe -0.03827; positive subperiods 2/4; recent104 -25.2101%.
- Standard and Bonferroni bootstrap lower bounds both negative. Independent arithmetic audit 3162/3162 row checks PASS.
- FOREIGN_INVESTOR_CAPITAL_FLOW broad family is CLOSED after 2/2 sibling tests; no third flow variant permitted.

## OSE Mini cash basis-change Stage A terminal result (2026-09-03)
- Data Gate PASS: 2,705 complete observations, 0 basis gaps, 0 timestamp conflicts after preregistered roll exclusion.
- Primary cumulative -94.0875%; stress -98.4236%; Sharpe -1.09006; bootstrap P(mean>0)=0.0008.
- Four fixed subperiods all negative; recent 504 observations -62.9681%.
- Independent audit: 21,640/21,640 row checks PASS; 5,410/5,410 timestamps resolved; all aggregate metrics exact.
- Governance: TERMINAL_FAIL_NO_RESCUE. No sign flip, basis-level, threshold, roll-window or horizon rescue.

## Dekansho-bushi post-publication terminal result (2026-09-03)
- Fixed published Jan-Jun long / Jul-Dec short rule tested only on 2014-01 through 2026-08 after the 2013 publication.
- 10bps cumulative -37.3361%; 20bps -40.4652%; annualized monthly Sharpe -0.11501; positive subperiods 2/4.
- Bootstrap P(mean>0)=0.3142; 95% lower mean monthly net -1.0325%. Recent 36 months +22.9545% is diagnostic only.
- Independent audit: 15,465/15,465 daily checks and 456/456 monthly checks PASS; all aggregates exact.
- Governance: TERMINAL_FAIL_NO_RESCUE; no OSE confirmation and no calendar-boundary or long/short-leg rescue.

## JNU Operational Framework v1.1 + live-shadow selftest (2026-09-03)
- Directional scout paused new formal families unless new direct Japan/Nikkei/OSE evidence passes the evidence gate.
- Operational Framework v1.1 forbids presenting judgmental scenario weights as calibrated probabilities and keeps formal shadow confidence at LOW/MEDIUM while directional modules remain zero.
- Live-shadow registrar/outcome/scorer selftest PASS: stale reference rejected, exact-product forecast/outcome accepted, n=1 correctly remains LIVE_SHADOW_ACCUMULATING.
- Selftest data remain in D:/Temp only and are not part of the real forecast ledger.

## JNU Operational Framework v1.2 decision protocol activation (2026-09-03)
- Four-block evidence fusion protocol selftest PASS: aligned 4-block MEDIUM, 2-block LOW, conflict/C-quality/event-risk fail-closed behavior confirmed.
- Live-shadow v1.1 amendment requires protocol-generated decision_trace; manual bias override and protocol-SHA tamper are rejected.
- No real live-shadow forecast existed before this amendment; all integration selftest records remain D:/Temp only.
- Framework v1.2 is authoritative; numeric directional probabilities remain uncalibrated/prohibited as model probabilities.

## Stage8 local source availability check (2026-09-03)
- Licensed N225microf_2026.zip ends at trading date 2026-08-31; SHA256 e6149c02097814f885a1414cb405ff687b2c4be0aeaef561d9a20b7881c58378.
- ingest_jnu_stage8_forward_local.py check-only returned NO_SOURCE_CHANGE; no derived panel or partial performance was modified/read.
- No safe authorized downloader/updater exists in the project; wait for legitimate licensed source-package extension, then check-only before --apply.

## Live-shadow atomic Git integrity chain (2026-09-03)
- Framework v1.3 / prereg v1.2 / implementation v1.2 / decision protocol v1 hash chain frozen before the first real live-shadow forecast.
- Atomic forecast/outcome tools require immediate Git commit+push for the real ledger; custom temp dirs remain available only for selftest.
- Integrity scorer independently recomputes decision trace, bias/confidence, outcome return, signed return and hit; SHA/tamper mismatches fail closed.
- Selftests PASS for normal chain and rejection of manual bias, outcome-return and framework-SHA tampering. Real ledger remains 0 forecasts / 0 outcomes.
