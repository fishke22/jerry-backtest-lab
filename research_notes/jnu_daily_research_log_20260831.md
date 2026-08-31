# JNU research daily log — 2026-08-31

## Purpose
This is the durable cross-session record of the approaches considered, work executed, results obtained, blockers discovered, and guardrails adopted on 2026-08-31. Future sessions must consult this file together with the canonical source registry, priority queue, family ledger, evidence matrix, framework status, and source-identity mapping before repeating source discovery or research attempts.

## Standing scientific rules applied today
- Evidence-first; no result may be promoted because it looks profitable.
- Proxy PASS is never true-OSE/JNU PASS.
- Execution/replay/source-alignment PASS is not alpha PASS.
- One formal information family at a time; no post-result rescue families.
- Strict OOS / walk-forward / causal timing / purge-embargo / multiple-testing governance remains binding.
- No paid data without explicit authorization.
- Licensed 225Labo raw data remains local-only; only non-reconstructable derived features, hashes, provenance, and aggregate results may be persisted remotely.
- No broker login or trading action.
- If no validated directional module exists, the decision engine must remain `NO_VALIDATED_DIRECTIONAL_EDGE`.

## 1. NEWS_STATE_LANGUAGE_SOURCE_G1-DI1 terminal closure
The final GDELT language/source family exhausted its frozen acquisition budget of three logical attempts. Final run 33348607397 ended `DATA_INCONCLUSIVE`, not FAIL, because the four-cell common panel remained incomplete. Statistical evaluation was not performed. No fourth acquisition attempt is allowed.

## 2. JNU Final Framework V3 freeze
The architecture was frozen before true-OSE outcomes. Directional, risk, event, source-weighting, and execution roles were separated. Combining modules is a new family requiring its own validation. Framework completion is allowed even with no validated directional alpha, in which case the valid completion state is `FRAMEWORK_COMPLETE_NO_VALIDATED_DIRECTIONAL_EDGE`.

## 3. Substitute-data strategy
A durable substitution rule was adopted: substitutes may unblock methodology, data-quality work, source alignment, or current-regime stress only. They inherit a proxy label and cannot satisfy true-OSE/JNU promotion unless preregistration explicitly allowed that source class before outcomes.

Sources investigated or added today include:
- GetData public Japan225 1-minute sample: active proxy only.
- Kaggle/HistData Nikkei 225 minute proxy: historical methodology proxy.
- Yahoo ^N225 daily: daily proxy only.
- Investing.com OSE Nikkei 225 mini daily history: true OSE identity but daily-only sanity source.
- Barchart JPX/SGX pages: true product identity; robust intraday history is paid/Premier and not adopted.
- Dukascopy Japan225: automation not used because current terms prohibit scraper/robot/data-mining acquisition without prior permission.
- FRED SP500: not adopted in the cloud pipeline under current rights interpretation.
- Mendeley daily Nikkei futures datasets: useful for daily method replication only, not intraday validation.

## 4. HAR-RSV public 2026 holdout G2
A frozen later-period public Japan225 1-minute holdout was executed using 5-minute RV/RSV construction, expanding OOS, QLIKE/MSE, and block bootstrap. GitHub Actions run 33357752091 completed successfully.

Terminal classification: `CURRENT_SAMPLE_PROXY_CONSISTENT` / true OSE still pending.
- Panel days: 130
- OOS days: 48
- HAR-RV QLIKE: -6.270437536541177
- HAR-RSV QLIKE: -6.280210481379707
- QLIKE improvement: +0.009772944838529621
- QLIKE bootstrap P: 0.9415
- HAR-RV MSE: 7.867502977866726e-06
- HAR-RSV MSE: 7.867017320930551e-06
- MSE improvement: +4.856569361748562e-10
- MSE bootstrap P: 0.975

Interpretation: this strengthens the pre-existing HAR-RSV proxy evidence across another regime, but has zero true-JNU promotion power. HAR-RSV remains the strongest high-value candidate for risk/sizing, pending true OSE mini Stage A and micro Stage B.

## 5. US-to-Japan intraday path public holdout G2
A frozen 2026 Japan225/SPY proxy holdout tested the literature-shaped FIRST30 negative-beta and LAST30 positive-beta hypotheses. GitHub Actions run 33358017603 completed successfully.

Terminal classification: `PROXY_PATH_CURRENT_SAMPLE_NOT_CONFIRMED`.
- FIRST30 final beta: -0.10815336033029892, but model MSE worsened, bootstrap P=0.297, sign accuracy worsened.
- LAST30 final beta: -0.03765976120071457, wrong sign; bootstrap P=0.788; sign accuracy worsened.
- Holm family pass: false.

Interpretation: later proxy evidence does not confirm the Iwanaga-shaped path and reinforces prior negative proxy G0. The true-OSE family remains unresolved rather than formally failed. No more proxy rescue variants are permitted; preserve exactly one frozen true-OSE test if qualifying data arrives.

## 6. CME NKD true-venue source discovery and feasibility
Public repository `axb0306/cme-futures-ohlc` was verified to contain true CME Nikkei 225 futures (NKD) tick/1m/5m and higher bars, sourced upstream from TopstepX/ProjectX. Visible NKD coverage was approximately 2026-03-08 to 2026-04-15, too short for standalone alpha validation.

A frozen source-alignment feasibility family `CME_NKD_JPN225_ALIGNMENT_G0` was run. Initial run 33359717960 failed because of a pandas index-alignment implementation defect; this was classified as data-integrity/engineering failure only. DI1 fixed positional value alignment without changing frozen research parameters.

Successful rerun 33359934341:
- common 5-minute bars: 7,305
- contemporaneous return correlation: 0.9221838112308237
- maximum absolute correlation lag: 0
- rolling 288-bar correlation median: 0.915635577176246
- promotion power: NONE

Interpretation: CME-side source alignment is technically feasible. This does not establish CME leadership, OSE leadership, directional alpha, or true-JNU validation.

## 7. DPD status after CME discovery
DPD changed from all-three-venues unavailable to: CME has a viable true-venue short sample; OSE and SGX matched-expiry historical intraday data remain blockers. DPD remains a dynamic source-weighting module only and cannot be used as a directional majority vote.

## 8. JPX/OSE official historical-data paths
Two distinct official paths were identified:
1. J-Quants DataCube sells OSE futures/options tick and one-minute OHLC history and exposes sample-data links on product pages.
2. JPX/OSE separately states that historical tick data may be provided for examination of trading methodology under certain conditions.

The public free-trial operational process describes a company applicant and asks for company/representative information. Therefore retail-individual eligibility is unresolved and must not be assumed.

Official enquiry route identified: JPX Market Innovation & Research Client Services / J-Quants DataCube contact form.

An inquiry draft was prepared but deliberately not submitted because no identity/company facts should be guessed.

## 9. JPX/OSE one-minute schema resolution
Even though the DataCube product page returned HTTP 403 to the current automated environment, the official public JPX data-specification PDF exposes the one-minute futures schema. This largely removes parser uncertainty.

Resolved core fields include:
`Trade_Date`, `Execution_Date`, `Index_Type`, `Security_Code`, `Session_ID`, `Interval_Time`, OHLC prices, `Trade_Volume`, `VWAP`, `Number_of_Trade`, `Record_No`, and `Contract_Month`.

Session codes:
- `999` = day session
- `003` = night session

This means HAR-RSV Stage A can be implemented from official 1-minute data without guessing schema once raw true-OSE history is obtained.

## 10. JPX/OSE product/security-code identity findings
Official JPX material provides the following durable mappings:
- Nikkei 225 Futures (large): 9-digit examples ending in `018`, e.g. `165030018`, `166030018`.
- Nikkei 225 mini: official March 2021 example `166030019`, establishing mini product suffix/index segment `19` for that coding scheme.
- Nikkei 225 micro: official current product category `NK225MCF`; official vendor codes include QUICK `115.n`, Bloomberg `JAIA <Index>`, LSEG `JNUcn`, CQG `F.US.MC225`.

Important unresolved item: the micro 9-digit local-security-code suffix has not yet been confirmed from a public primary-source issue example. Do not infer it from vendor codes.

A coverage discrepancy was also recorded: current English DataCube material was seen with mini availability from 2006-09-01, while other JPX/225Labo evidence shows 2006-07-18. Treat this as a product/file/publication-boundary discrepancy until actual acquired manifest data resolves it; do not impute dates.

## 11. 225Labo local-only true-OSE path
225Labo was re-verified as a high-value personally licensed true-OSE source and is also used in formal Nikkei futures academic work.

Current access evidence:
- Nikkei 225 mini minute data from 2006, with 1/3/5/10/15/20/30/60-minute intervals.
- Nikkei 225 micro minute data from 2023-07-24, with the same family of intervals.
- Registered-member downloads are free, but the downloader-only license prohibits third-party provision/sale or similar transfer.

Adopted architecture:
1. local login/download only;
2. verify hashes and parse locally;
3. perform session/data-integrity transforms locally;
4. upload only non-reconstructable derived features/results + hashes/provenance;
5. Stage A: long-history Nikkei mini frozen HAR-RSV confirmation;
6. Stage B: exact-product JNU micro confirmation only if Stage A passes and with no retuning.

Remote Desktop Commander was checked repeatedly today; the authorized Windows device remained offline. Therefore no 225Labo raw file, broker login, or trading environment was touched.

## 12. SGX historical tick archive lead
Multiple public GitHub projects independently document the legacy SGX derivatives historical endpoint family and files:
- `WEBPXTICK_DT`
- `TickData_structure.dat`
- `TC.txt`
- `TC_structure.dat`

Public downloader projects report history back to at least 2004-07-23, and another project reports earliest files from 2002-10-01. These prove technical existence only.

Current SGX Market Data Policy effective 2026-07-01 governs display, non-display, redistribution, and reporting. Therefore no automated bulk acquisition or cloud retention is permitted under current evidence. A public downloader is not current legal authority.

## 13. SGX Nikkei product identity mapping
Current SGX official product material confirms:
- `NK` = SGX JPY Nikkei 225 Index Futures (outright/strategy)
- `NKTI` = Trade-At-Index-Close variant
- `NU` = SGX USD Nikkei 225 Index Futures
- `NS` = SGX Mini Nikkei 225 Index Futures

This is a substantial identity advance, but legacy `TC.txt`/`WEBPXTICK` historical archive codes are not yet proven to use these exact current codes. The correct next task is a metadata-only mapping attempt, not bulk tick download.

## 14. Other source findings retained today
- Barchart JPX mini intraday history is effectively a paid/Premier path and was not adopted.
- Tick Data and other commercial vendors prove rich OSE/SGX history exists but remain outside the zero-extra-cost policy.
- Academic literature confirms historical OSE and SGX tick datasets have been used in research, including SGX "Tick Data and Daily Statistics", but downloadable public copies were not verified.
- BOJ MPM event-volatility literature is meaningful but the required robust free intraday Nikkei 225 VI/VI-futures history remains blocked.
- OSE order imbalance remains literature-only because signed trades/quotes/order-book data are unavailable under approved free paths; OHLC/volume must not be used to fabricate imbalance.
- Cboe LTV remains blocked because verified free official history was not found; VIX/SKEW must not be relabeled as LTV.

## 15. Cloud/GitHub engineering cleanup
Resolved workflows were changed to manual dispatch to prevent unrelated new request files from accidentally retriggering old proxy workflows. Accidental runs 33357752096 and 33358017642 are engineering noise, not research attempts.

## 16. Canonical state at end of day
- Framework: JNU Final Framework V3, architecture frozen.
- `VALIDATED_JNU_MODULE = 0`.
- Validated directional modules = 0.
- Decision engine = `NO_VALIDATED_DIRECTIONAL_EDGE`.
- HAR-RSV = strongest risk/sizing candidate, true-OSE confirmation pending.
- US->Japan FIRST/LAST30 directional path = weak proxy evidence; one frozen true-OSE test only if data arrives.
- DPD = CME-side feasible, OSE/SGX still blocked.
- Order imbalance = literature-only data-blocked.
- Framework research state remains `FRAMEWORK_RESEARCH_COMPLETE_DATA_BLOCKED` until true-OSE or genuinely new qualifying evidence/data becomes observable.

## 17. Durable files created/updated today
Canonical or supporting files include:
- `config/jnu_final_framework_v3_prereg.json`
- `config/jnu_framework_completion_criteria_v1.json`
- `config/jnu_true_ose_execution_package_v1.json`
- `config/jnu_framework_completion_status_v1.json`
- `config/jnu_research_priority_queue.json`
- `config/jnu_evidence_matrix_v1.json`
- `config/jnu_family_attempt_ledger.json`
- `config/jnu_substitute_source_registry_20260831.json`
- `config/jnu_source_identity_mapping_20260831.json`
- `research_notes/jnu_new_source_discovery_cme_nkd_sgx_20260831.md`
- `research_notes/jnu_true_ose_free_access_paths_20260831.md`
- `research_notes/jnu_jpx_ose_access_inquiry_draft_20260831.md`
- `research_notes/jnu_225labo_current_access_validation_20260831.md`
- `research_notes/jnu_access_resolution_round2_20260831.md`
- this file: `research_notes/jnu_daily_research_log_20260831.md`

## 18. Mandatory next-session read order
Before saying that JNU data cannot be found or before starting another proxy family, read:
1. `research_notes/jnu_daily_research_log_20260831.md`
2. `config/jnu_data_source_registry.json`
3. `config/jnu_substitute_source_registry_20260831.json`
4. `config/jnu_source_identity_mapping_20260831.json`
5. `config/jnu_research_priority_queue.json`
6. `config/jnu_family_attempt_ledger.json`
7. `config/jnu_evidence_matrix_v1.json`
8. `config/jnu_framework_completion_status_v1.json`

## 19. Next highest-value work frozen at end of day
A. Resolve the Nikkei 225 micro 9-digit JPX local-security-code example/suffix from an official primary source or issue master; do not guess.
B. Resolve SGX legacy `TC.txt`/`TC_structure` metadata fields and map current `NK`/`NS` identifiers to historical archive identity without bulk tick download.
C. Continue JPX individual eligibility/rights resolution. If not suitable, fall back to 225Labo local Stage A as soon as the authorized Windows device is online.
D. Do not open another proxy directional family merely to keep testing.


## 20. QROS local-source inventory after device reconnection
The authorized Windows device returned online and `D:\QROS` was inspected read-only. A mature `nikkei_multifactor_engine` plus substantial `data\ose_free` corpus already exists. The key correction is that exact true-OSE daily/session data are locally available: Micro has 364 distinct days (2025-02-03 to 2026-07-30), while the common day-session Mini corpus has 1,250 distinct days (2015-12-01 to 2026-07-30). QROS also contains hundreds of official JPX Daily Report PDFs, NDL archive metadata/parsed rows, monthly/annual JPX files, source hashes, receipts and DQ/provenance artifacts.

A direct normalized JPX Daily Report row for 2025-02-03 confirms Micro `trading_code=160030023`, multiplier 10 and tick size 5. This independently cross-checks the JPX target-index suffix/classification `23` discovered from official DataCube specifications.

The prior QROS research already built `jnu_continuous_micro_v1` from exact OSE Micro daily reports: 364 rows, 19 actual contracts, 18 rolls. Its old exploratory backtest PnL is not imported into the current JNU validated lineage; QROS itself marks formal strategy acceptance and positive expectancy as false.

Critically, the common dataset is DAY/SESSION grain, not minute grain. Therefore it cannot satisfy the frozen HAR-RSV 5-minute RV/RSV gate, FIRST/LAST30 path tests, DPD lead-lag, or order-imbalance research. The blocker is narrowed to true-OSE 1m/5m intraday history, not true-OSE history in general.

Existing realtime/Yuanta research artifacts were checked only through non-account manifests/snapshots. No historical JNU capture was found. Static FunctionList evidence confirms JNU quote-code mappings, but no new broker login or market-data request was performed.

Detailed inventory: `research_notes/jnu_qros_local_source_inventory_20260831.md`.

## 21. Revised next action after QROS discovery
1. Do not repeat JPX/NDL archive discovery already completed in QROS.
2. Reuse QROS parsers, source receipts, DQ and provenance machinery.
3. Treat the exact Micro 364-day and Mini 1,250-day corpora as daily/session evidence only.
4. Search/acquire true OSE Mini 1m/5m locally, with 225Labo the preferred no-extra-cost personal-use path; raw remains local-only.
5. If local 225Labo minute acquisition is unavailable, continue JPX historical-trial eligibility resolution.
6. Never synthesize 5-minute RV/RSV from daily/session OHLC.


## 22. 225Labo authenticated-acquisition boundary
Current 225Labo pages were rechecked after the local device came online. Nikkei 225 mini minute history is offered from 2006 onward in 1/3/5/10/15/20/30/60-minute intervals; Micro minute history is offered from 2023-07-24. Download requires member login. 225Labo's download terms state that the data are privately collected/created, are provided without warranty, and are intended for the individual data user's own learning/verification; third-party provision/redistribution is prohibited. Therefore the adopted boundary remains: login and raw files local only, no credentials/cookies/authenticated URLs in GitHub/cloud, and only non-reconstructive derived RV/RSV panels/hashes may leave the local machine.

The local default browser was opened to the 225Labo login page and Mini download page to make the required human authentication step available. No password, session cookie, or browser credential was read or exported.

A generic fail-closed Phase-A schema auditor was added at `scripts/inspect_225labo_local_sample.py`. It supports local CSV/TXT/XLSX/XLSM/ZIP structure inspection, hashes the raw file, emits only structural/header metadata, and never prints raw market-data rows. A concrete 225Labo parser remains prohibited until an actual user-downloaded sample is observable.

## 23. QROS July source report supersession
Two QROS reports dated 2026-07-12 stated that the JPX Daily Report was settlement-only and that no authoritative OSE Micro historical OHLC/volume/OI had been obtained. Those statements were correct for that task's knowledge state but are superseded by later QROS work from August: hundreds of JPX public Daily Report PDFs were downloaded and parser v1.0.2 extracted explicit night/day OHLC, settlement, volume and open interest for Large/Mini/Micro contract rows. The exact Micro common-day corpus now has 364 distinct days and the Mini corpus 1,250 distinct days.

Future sessions must use the later provenance/DQ artifacts rather than treating the 2026-07-12 report as current source availability. This supersession still does not create minute/tick history; the remaining blocker is true OSE 1m/5m intraday history.


## 24. 225Labo Mini intraday acquisition complete
The authorized local Windows session completed the 225Labo Nikkei 225 Mini annual intraday acquisition for every year 2006 through 2026.

Local raw storage boundary:
`D:\QROS\data\personal_licensed\225labo\mini\raw`

Inventory:
- 2006-2011: legacy direct XLS annual files (225miniYYYYd.xls).
- 2012-2026: annual ZIP containers (N225minif_YYYY.zip), containing XLS for early years and XLSX for later years.
- Every annual generation contains a source-provided `5min` sheet. The later workbooks also expose 1/3/5/10/15/20/30/60min plus daily sheets; older workbooks use equivalent minute sheets with some legacy workbook-layout differences.
- 2006 has a one-row descriptive preamble before the standard header; parser support was frozen by finding the exact header within the first 12 rows rather than guessing prices.
- 225Labo date labels were empirically verified as OSE trading-date labels: each date group lists the night session first and the same trading-date day session afterward. No artificial +1 day shift is applied.

Raw 225Labo files remain local-only. They are not uploaded to GitHub/cloud. Future GitHub backtests will use only non-reconstructive daily RV/RSV derived features, source hashes, DQ manifest and results.

The local adapter is `scripts/build_225labo_mini_rvrsv_local.py` and now:
- supports direct XLS and ZIP-contained XLS/XLSX generations;
- uses source-provided 5min as the frozen primary measurement;
- applies `config/jnu_session_calendar_versions.json` historically;
- never forms returns across session boundaries;
- supports 1min-vs-5min measurement QA separately so primary 5m build is not delayed;
- has no pandas/NumPy dependency locally, avoiding the QROS Python ABI mismatch.

True-OSE Stage A was preregistered before outcome inspection in:
`config/jnu_har_rsv_true_ose_mini_stage_a_g1_prereg.json`.

The cloud runner/workflow are:
- `scripts/process_jnu_har_rsv_true_ose_mini_stage_a_g1.py`
- `.github/workflows/jnu-har-rsv-true-ose-mini-stage-a-g1.yml`

Current state at this log point: true-OSE Mini intraday acquisition COMPLETE; derived 5m RV/RSV build RUNNING; no Stage A statistical outcome inspected yet.


## 25. HAR-RSV true-target Stage 3 completed
The full preregistered true-target sequence completed without retuning.

### Stage A — true OSE Nikkei 225 Mini
- Status: `TRUE_OSE_MINI_STAGE_A_PASS`
- Valid run: 33388746345
- 4,442 OOS days (2008-09-08 → 2026-08-31)
- QLIKE improvement: +0.0027914101288612917; 5-day block-bootstrap P(improvement>0)=1.0
- MSE improvement: +4.783249414627292e-10; P=0.9875

### Stage B — exact-product OSE Nikkei 225 Micro (JNU)
- Status: `TRUE_JNU_MICRO_STAGE_B_PASS`
- Valid run: 33389857914
- 270 OOS days (2025-08-13 → 2026-08-31)
- QLIKE mean improvement: +7.292861808050662e-05; bootstrap P=0.522
- MSE mean improvement: +1.1450264024518442e-09; bootstrap P=0.9685
- Frozen Stage-B gate passes because both loss improvements are positive and at least one bootstrap probability is >=0.95.

Scientific interpretation:
- HAR-RSV now passes promotion-pipeline Stage 3 TRUE_TARGET_DATA_CONFIRMATION.
- New state: `INFORMATION_STATE_CANDIDATE`.
- Permitted research role: volatility/risk state only.
- It is not directional alpha, not a validated trading rule, and not Stage 9 `VALIDATED_JNU_MODULE`.
- Any use for sizing, stop distance or confidence that changes positions/risk must be separately preregistered and pass the applicable downstream stages.

## 26. Repository visibility and public-data boundary
`fishke22/jerry-backtest-lab` was changed from PRIVATE to PUBLIC on 2026-08-31 after a pre-publication current-tree and Git-history scan found no tracked credentials/private keys/common token patterns and no 225Labo raw XLS/XLSX/ZIP files. Only non-reconstructive daily derived RV/RSV panels, hashes, manifests, code and research results are public. Personally licensed 225Labo raw minute files remain local-only under `D:\QROS\data\personal_licensed\225labo\...`.


## 27. True-JNU prior-SPX intraday path terminal result
The single frozen true-JNU family `INTRADAY_PATH_US_TO_JNU_TRUE_G1` was executed after exact-product JNU minute data became available.

Data:
- JNU Micro daily path features derived locally from 225Labo 1-minute bars; 796 causal-aligned days.
- Predictor: exact S&P 500 index (^GSPC) close-to-close return from pinned Kaggle dataset version 732, raw not persisted in the repo.
- Valid run: 33391992462; artifact 9757824371.

Terminal result: `REJECT_TRUE_JNU_CURRENT_SPEC`.
- H1 FIRST30 beta sign matched negative literature direction, but Pboot(MSE improvement>0)=0.84 < 0.95.
- H2 LAST30 final beta was positive as expected, but mean MSE improvement was negative and Pboot=0.454.
- H3 state interaction also worsened mean MSE; Pboot=0.354.
- Holm family pass=false.

Interpretation: coefficient signs resembling the paper are insufficient; exact-product JNU predictive information did not clear the preregistered OOS family gate. This family is closed. Do not tune 30-minute windows, switch to ES/NQ/SPY/QQQ, drop cells, or add indicators/regimes to rescue it.

Framework implication:
- HAR-RSV remains the only Stage-3 true-JNU information-state candidate, and only for volatility/risk.
- Validated directional modules remain 0.
- Decision engine remains `NO_VALIDATED_DIRECTIONAL_EDGE`.


## 28. SGX DPD rights blocker and BOJ family unblocked
A fresh SGX source/rights audit was completed after OSE Mini/Micro minute data became available.

### TRUE_VENUE_DPD_OSE_SGX_CME
- OSE side: genuine minute history available locally through 225Labo.
- CME side: public NKD short sample already passed source-alignment feasibility.
- SGX side: current NK/NS identity and legacy TC/TickData structure are known, but no free third-party matched-expiry SGX Nikkei intraday dataset with explicit quantitative/non-display/retention rights was verified.
- SGX's 2026 Market Data Policy covers historical data and regulates non-display usage; SGX website terms also restrict copying/storage/derivative works without permission. Public GitHub projects contain downloader/index code, not licensed raw SGX market data. Barchart long-history 1-minute downloads are Premier/paid.
- Therefore DPD is now `DATA_RIGHTS_BLOCKED_SGX_INTRADAY`. Do not bulk-download legacy SGX archives or pay for Barchart/Tick Data without explicit authorization.

### BOJ_MPM_EVENT_VOLATILITY
The prior blocker `BLOCKED_ON_INTRADAY_OUTCOME_DATA` is obsolete because genuine OSE Mini 2006-2026 and exact JNU Micro 2023-2026 minute data are now locally available. The family is promoted to event-timestamp construction/pre-prereg status only. No price outcome may be inspected until the official BOJ release-time corpus and statistical design are frozen.

The active formal research slot is now reserved for `BOJ_MPM_TRUE_OSE_EVENT_VOLATILITY_G1`.


## 29. BOJ MPM true-target Stage 3 completed
The preregistered `BOJ_MPM_TRUE_OSE_EVENT_VOLATILITY_G1` family completed both true-target stages without window/threshold retuning.

Event-side provenance:
- 226/226 post-Mini-launch BOJ policy releases have exact official JST release times.
- Fixed eligibility based only on release time and historical OSE continuous-session geometry produced 192 eligible events: 170 Mini Stage A, 22 exact-JNU Micro Stage B.
- Primary windows were frozen before price-outcome inspection: baseline [-40,-10) and event [-10,+20).

Data-integrity revisions before statistical outcome inspection:
- DI1 `7c968b8...`: old XLS files split 1-minute history across multiple `1min*` sheets; concatenating all shards restored Stage A from an erroneous 104/170 usable events to 170/170.
- DI2 `909391d...`: manifest-schema completion only.
- Neither revision changed event eligibility, windows, bootstrap, thresholds, or hypothesis.

### Stage A — true OSE Nikkei 225 Mini
- Run: 33396821958
- Status: `TRUE_OSE_MINI_BOJ_EVENT_VOL_STAGE_A_PASS`
- 170 usable events
- Mean log(EventRV/BaselineRV): +0.4450516453986761
- Median: +0.2951189323620672
- Bootstrap P(mean>0): 0.981
- 95% CI: [0.029547011546631502, 0.7571929210770287]

### Stage B — exact OSE Nikkei 225 Micro (JNU)
- Run: 33397255940
- Status: `TRUE_JNU_MICRO_BOJ_EVENT_VOL_STAGE_B_PASS`
- 22 usable events
- Mean log(EventRV/BaselineRV): +1.6034692468630831
- Median: +1.7268933093975936
- Bootstrap P(mean>0): 1.000
- 95% CI: [1.0789356833387151, 2.126909061305105]

Scientific interpretation:
- BOJ MPM event-volatility passes promotion-pipeline Stage 3 as an `EVENT_RISK_INFORMATION_STATE_CANDIDATE`.
- It is not directional alpha and not a live entry/size/stop rule.
- Any entry blackout, size reduction, stop widening, or confidence adjustment is a new downstream translation requiring preregistration and validation.
- Framework now has two Stage-3 risk/information candidates: HAR-RSV and BOJ MPM event volatility. Validated directional modules remain 0; decision output remains `NO_VALIDATED_DIRECTIONAL_EDGE`.


## 30. Momentum-reversion Stage A terminal result
The preregistered `INTRADAY_MOMENTUM_REVERSION_TRUE_JNU_G1` family completed its true-OSE Mini Stage A on 4,170 usable trading days.

- Valid run: 33399653907; artifact 9760719973.
- Overall status: `TRUE_OSE_MINI_MOMREV_STAGE_A_FAIL`.
- H1 1-minute momentum: FAIL. Mean daily signal payoff = -5.914279386709916e-05; directional accuracy = 0.4081390742120026; bootstrap P(mean>0)=0.0.
- H2 non-overlapping 10-minute mean reversion: PASS inside the family. Mean daily signal payoff = +3.836712557711084e-05; directional accuracy = 0.522454101654589; bootstrap P=1.0.
- Holm family pass = false.
- Exact-JNU Micro Stage B is prohibited by preregistration.

Interpretation:
The literature-shaped two-cell family is terminally rejected. The strong 10-minute reversal result cannot be isolated after inspection, and the failed 1-minute momentum sign cannot be flipped into a new signal as a rescue. Any future related family requires substantively independent evidence and a new preregistration before outcomes.
