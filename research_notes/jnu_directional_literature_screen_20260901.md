# JNU directional literature screen — 2026-09-01

Purpose: find a **substantively independent, direct Nikkei/OSE directional hypothesis** after three recent preregistered directional families failed. No new family is opened unless the evidence is both independent and implementable with rights-clean/no-extra-cost data.

## Current conclusion

**NO_NEW_FORMAL_DIRECTIONAL_FAMILY_OPENED_YET.**

The strongest newly reviewed papers are scientifically relevant, but each fails at least one of the current governance gates: independent-from-failed-families, current structural relevance, exact target alignment, or rights-clean/free data availability.

## Screened evidence

### 1. Shyy & Shen — OSE/SIMEX open autocorrelation

Paper: *A comparative study on interday market volatility and intraday price transmission of Nikkei/JGB futures markets between Japan and Singapore*.

Direct result: for Nikkei futures, both OSE and SIMEX show significantly higher variance and **negative first-order autocorrelation at the open** than at the close; intermarket Granger causality is bidirectional.

Disposition: **DO_NOT_OPEN_NOW — SELECTION-BIAS/ADJACENCY RISK.**

Reason: this is direct Nikkei/OSE evidence, but an opening-specific short-horizon reversal family is too close to the already-inspected `INTRADAY_MOMENTUM_REVERSION_TRUE_JNU_G1`, where generic 1-minute momentum failed strongly and 10-minute reversal passed only inside a failed family. Opening an open-only reversal immediately after observing that pattern would create an unacceptable post-selection interpretation risk.

### 2. Yoshikawa (2001) — intraday reversal/time-of-day

Paper: *Intraday Price Behavior of the Nikkei Stock Average and Nikkei 225 Futures*, Securities Economics Research No. 33, Japan Securities Research Institute.

Direct evidence: minute data on Nikkei 225 spot and futures; intraday returns, volatility, reversal and lead/lag are examined. The institutional summary reports strong time-of-day variation; the futures reversal behavior differs from spot and is substantial.

Disposition: **DO_NOT_OPEN NOW — SAME ADJACENCY RISK.**

Reason: reversal/time-of-day is not sufficiently independent from the just-failed momentum/reversion family to satisfy the current directional checkpoint.

### 3. Hiraki, Maberly & Takezawa (1995) — end-of-day OSE futures information content

Paper: *The information content of end-of-the-day index futures returns: International evidence from the Osaka Nikkei 225 futures contract*, Journal of Banking & Finance 19, 921-936. DOI: `10.1016/0378-4266(94)00064-A`.

Direct result: the unexpected component of end-of-day OSE Nikkei futures returns is positively related to overnight spot returns and to spot trading-period returns over the next two trading days.

Disposition: **DO_NOT_OPEN CURRENT JNU FAMILY.**

Reasons:
- The target in the published result is subsequent **spot** return, not subsequent OSE/JNU futures return.
- The historical OSE end-of-day extended session studied in the paper was subsequently eliminated; the structural mechanism is not the same as today's OSE day/night architecture.
- Recasting the result into a modern JNU futures target would require a new hypothesis not directly established by the paper.

### 4. Qin, Green & Sirichand (2023) — nonlinear spot/futures error correction

Paper: *Spot–Futures Price Adjustments in the Nikkei 225: Linear or Smooth Transition? Financial Centre Leadership or Home Bias?*, Journal of Risk and Financial Management 16(2):117. DOI: `10.3390/jrfm16020117` (CC BY 4.0).

Direct results:
- Nikkei spot/futures and cross-market futures exhibit nonlinear smooth-transition error correction.
- Futures led spot before the global financial crisis, while spot led afterwards.
- SGX/CME leadership is important in cross-border price discovery.

Disposition: **RESEARCH LEAD, NOT CURRENT FAMILY.**

Reasons:
- A proper modern implementation needs contemporaneous rights-clean Nikkei spot plus OSE and ideally SGX/CME matched-contract data.
- SGX matched-expiry intraday remains rights-blocked in current governance.
- Nikkei spot machine-processing/data rights are not yet cleared for the required historical panel.
- This is better treated as a future DPD/basis/error-correction family after data-rights resolution, not as an OSE-only directional shortcut.

### 5. Frino & West (2003) / related price-discovery literature

Paper: *The impact of transaction costs on price discovery: Evidence from cross-listed stock index futures contracts*, Pacific-Basin Finance Journal 11, 139-151. DOI: `10.1016/S0927-538X(02)00111-7`.

Direct result: both OSE and SIMEX Nikkei futures lead the Nikkei 225 Index, while SIMEX strongly leads OSE futures in their sample.

Disposition: **MERGE INTO DPD DATA-RIGHTS BLOCKER.**

Reason: scientifically supports multi-venue price discovery, but formal execution still requires rights-clean matched-expiry SGX intraday data. Do not create a proxy directional family.

### 6. Kao et al. (2015) — US/Japan futures cross-time-zone linkage

Paper: *Price linkage between the US and Japanese futures across different time zones: An analysis of the minute-by-minute data*, Journal of International Financial Markets, Institutions and Money 34, 321-336. DOI: `10.1016/j.intfin.2014.12.002`.

Direct result: information leadership changes over time between US and Japanese futures; short-run Granger causality and long-run price discovery agree.

Disposition: **NO NEW FAMILY.**

Reason: this is too close to the already terminal `INTRADAY_PATH_US_TO_JNU_TRUE_G1` / cross-market transmission theme to count as a substantively independent new directional family without a clearly different ex-ante target and dataset.

### 7. Smales (2026) — news sentiment and Nikkei futures returns

Paper: *When news travels: The role of sentiment in CME Nikkei futures returns*, Research in International Business and Finance 81, 103223. DOI: `10.1016/j.ribaf.2025.103223`.

Direct result: Japanese/English fundamental news sentiment is associated with Nikkei futures returns; predictive quantile regressions are reported out to longer horizons.

Disposition: **HIGH-VALUE LEAD, DATA-MEASUREMENT BLOCKED.**

Reason: the published measurement uses Thomson Reuters News Analytics (TRNA), a proprietary dataset. Substituting GDELT or another free sentiment engine would create a different measurement family. The prior free-news acquisition family also ended DATA_INCONCLUSIVE. No paid TRNA path is adopted.

### 8. CFTC trader-position / herding literature

Direct Nikkei-futures position data are publicly available from CFTC for CME Nikkei contracts, and herding literature documents that trader positions are correlated with current/past returns.

Disposition: **NOT ENOUGH FOR A DIRECTIONAL PREDICTIVE FAMILY YET.**

Reason: the currently reviewed evidence is primarily contemporaneous/behavioral rather than a clean pre-specified future-return prediction. Do not infer predictive power merely because positions and past/current returns are correlated.

### 9. Simple technical trading-rule evidence

Raj & Sweidan, *Profitability of trading rules using Nikkei futures transaction data*, uses Nikkei futures transaction data on SGX and finds simple filter/channel rules are not abnormally profitable once higher transaction costs are considered.

Disposition: **NEGATIVE EVIDENCE AGAINST OPENING GENERIC TECHNICAL-INDICATOR FAMILIES.**

Do not open RSI/MACD/filter/channel searches merely because they are easy to test.

## Governance consequence

The directional checkpoint remains active:

- validated directional modules = 0;
- do not lower gates;
- do not rescue the 10-minute reversal cell;
- do not open an opening-only reversal family immediately after the failed generic momentum/reversion family;
- do not open a modern EOD family from an obsolete OSE extended-session structure;
- do not treat spot/futures or SGX/OSE price-discovery evidence as executable until data rights are resolved;
- do not substitute proprietary TRNA sentiment with a free source and call it the same published family.

## Highest-value next search directions

1. Search for **direct OSE/Nikkei futures return predictability from a structurally distinct mechanism** that can be computed from existing OHLCV or a clearly free official/public source.
2. Search newer Japanese institutional repositories (CiNii, JSRI, university repositories) for post-2015 OSE/Nikkei studies with explicit future-return forecasts, not merely volatility, contemporaneous explanation or price discovery.
3. Search for direct Nikkei futures evidence using public macro announcement surprise data where the surprise variable has an official/free source and causal release timestamps; avoid reopening BOJ MPM direction unless the paper explicitly establishes directional predictive content.
4. Revisit nonlinear spot/futures error correction only after a rights-clean historical Nikkei spot input and SGX path are verified.

No formal information family is active after this screen.