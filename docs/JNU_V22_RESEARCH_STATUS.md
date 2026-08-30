# JNU V2.2 Research Status

Updated: 2026-08-31

## Standing interpretation

No module is currently a `VALIDATED_JNU_MODULE`.

| Module | First engine | Nautilus second engine | Overfit / multiple testing | Research disposition |
|---|---|---|---|---|
| dynamic_price_discovery | CLOUD PILOT COMPLETE | not eligible yet | proxy-only; venue coverage gate failed | CONDITIONAL_ARCHITECTURE_ONLY / NOT ALPHA |
| intraday_volatility_HAR_RSV_DI1 | PROXY METHOD PASS | not eligible yet | index proxy only; true JNU confirmation pending | RISK-STATE CONFIRMATION CANDIDATE / NOT DIRECTION ALPHA |
| intraday_path_US_G0 | PROXY SCREEN FAIL | not eligible | fixed FIRST/LAST 30m family failed OOS gate | PROXY NEGATIVE / TRUE JNU UNRESOLVED |
| phase4b_USDJPY_1d | FAIL | not eligible | bootstrap 0.7445; sign accuracy worsened | REJECT_CURRENT_SPEC |\n| phase4b_news | DATA INCONCLUSIVE | not eligible | GDELT acquisition did not complete under bounded conservative protocol | QUARANTINE_CURRENT_SOURCE_PATH |
| volatility_regime | PASS_CANDIDATE | PASS_ENGINE_REPLAY | FAIL_OVERFIT_GATES | QUARANTINE / independent confirmation only |
| cross_market_confirmation | PASS_CANDIDATE | PASS_ENGINE_REPLAY | FAIL_OVERFIT_GATES | REJECT_OVERFIT |
| trend_momentum | FAIL | not eligible | not run | REJECT |
| breakout | FAIL | not eligible | not run | REJECT |
| drawdown_repair | FAIL | not eligible | not run | REJECT |
| relative_strength_ndx | FAIL | not eligible | not run | REJECT |
| SMA baseline | FAIL | not eligible | not run | BASELINE_ONLY |

## Dynamic Price Discovery disposition

The preregistered cloud pilot found strong same-bar synchronization but weak and unstable nonzero lead-lag effects. The 1-minute OOS split contained only two test trading days and is insufficient. In the 5-minute robustness run (15 OOS test days), ES/NQ incremental next-bar information for the CME Nikkei proxy was near zero or negative in most session tests. Therefore:

- DPD remains useful as a **session-aware source-weighting architecture**.
- It is **not** a validated directional alpha signal.
- Fixed NQ/ES weights or a revived cross-market majority vote are prohibited.
- Formal venue-leadership validation remains blocked until approved OSE and SGX intraday data are available.
- The strongest no-extra-cost OSE candidate currently identified is 225Labo, subject to personal-use/member-access and storage-rights review.

## Why volatility_regime is quarantined rather than promoted

It showed strong structural robustness under CPCV and low PBO, but did not clear the pre-registered Deflated Sharpe Ratio or family-wise multiple-testing significance thresholds. It may be tested on genuinely independent data with the rules frozen, but it must not be tuned against the same 2023-2026 sample to force a pass.

## Why cross_market_confirmation is rejected

Its PBO was extremely high and CPCV positive-path consistency was below the required threshold. The apparent first-engine and second-engine profitability is therefore not sufficient evidence of a durable edge.

## Rule

Do not rescue failed modules by widening parameter grids, changing thresholds after seeing results, or selectively dropping bad periods. A new hypothesis must be pre-registered as a new research candidate.


## Intraday volatility HAR-RSV DI1 disposition

A data-integrity correction was required because the TSE morning cash session ended at 11:00 before 2011-11-21. The original proxy result is retained for audit; DI1 changed only the historical session mask and left the 5-minute sampling, HAR 1/5/22 windows, model family, bootstrap settings, and pass thresholds frozen.

DI1 results on the 2011-2018 Nikkei index minute proxy:

- OOS: 1,524 days (2013-01-22 to 2018-12-31).
- HAR_LEVERAGE remained a fail.
- HAR_RSV achieved MSE bootstrap P(improvement > 0) = 0.9585 and therefore passed the preregistered proxy-method gate.
- QLIKE bootstrap support remained weak (0.6835), and the source is not OSE/JNU futures.

Disposition:

- **Do not promote as directional alpha.**
- Retain HAR-RSV as a frozen **volatility/risk-state confirmation candidate** for true OSE/JNU minute data.
- If confirmed on true JNU data, its allowed role is risk state, position sizing, stop-distance normalization, and confidence adjustment.
- Do not retune sampling interval, HAR windows, semivariance definition, or bootstrap gate on the 2011-2018 proxy sample.

## Intraday Path prior-U.S.-return G0 disposition

The 2026 direct Nikkei-futures hypothesis was screened with frozen FIRST_30M and LAST_30M states on pinned JPXJPY/SPXUSD minute proxies, strict prior-completed-U.S.-session availability, and historical timezone/session corrections.

Proxy G0 results:

- Derived aligned panel: 713 days.
- FIRST_30M coefficient had the expected negative sign, but incremental OOS MSE worsened and hit rate fell; bootstrap P(improvement > 0) = 0.1385.
- LAST_30M coefficient did not preserve the expected positive sign; bootstrap P(improvement > 0) = 0.6175.
- Family gate: **FAIL**.

Disposition:

- **Do not admit this proxy family to the JNU framework.**
- Do not change 30-minute windows, swap SPX for NQ, or add technical indicators to rescue the proxy.
- Because this is an index-proxy screen with limited aligned coverage, the 2026 true-futures hypothesis is not declared disproven. A future true-JNU confirmation may be run only with the frozen Generation-1 specification.

## Phase4B execution note

USDJPY and six preregistered GDELT news-state tests have not produced a research result yet. Previous attempts were terminated by the GitHub Actions 15-minute job limit rather than by model/data exceptions. The control-plane timeout has been increased to 45 minutes without changing any research specification.


## Phase4B USDJPY 1-day incremental-state disposition

The existing preregistered USDJPY subtest was executed independently from GDELT retrieval as a checkpoint, with all parameters read directly from the original Phase4B request. This is not a new hypothesis family.

- OOS days: 642.
- Baseline MSE: 0.0003107946272.
- With USDJPY MSE: 0.0003078968195.
- Mean MSE improvement: 2.8978e-06.
- Block-bootstrap P(improvement > 0): **0.7445**, below the frozen 0.95 gate.
- Sign accuracy: **54.67% -> 54.05%**, violating the preregistered non-worsening condition.
- High-VIX diagnostic P(improvement > 0): 0.885; below the gate.
- Low-VIX diagnostic mean improvement was negative.

Disposition: **REJECT_CURRENT_SPEC**.

Do not promote a universal one-day USDJPY state, and do not rescue it by selecting only the high-VIX subset after observing these results. A future FX hypothesis must be preregistered as a new family using independently justified timing/regime structure or new data.


## Phase4B broad GDELT news-state disposition

The six-category preregistered news family did **not** produce a valid statistical result. This is not a model FAIL.

Data-acquisition audit:
- Multi-year GDELT DOC queries timed out.
- Annual chunking successfully completed many category/mode/year cells.
- Adaptive subdivision still encountered service-level connection refusals for some cells.
- A final conservative run used a single paced connection plus cumulative Actions cache, but reached the 45-minute bounded execution limit before the full panel completed.
- The final run preserved successfully downloaded cache rather than discarding it.

Disposition: **DATA_INCONCLUSIVE / QUARANTINE_CURRENT_SOURCE_PATH**.

Rules:
- Do not count this as evidence that news sentiment has no JNU value.
- Do not lower statistical gates or drop hard-to-fetch categories to manufacture a result.
- Do not keep retrying the same broad GDELT DOC family indefinitely.
- Any next news generation must be a new preregistered family with an independently justified structure and a more reliable data-acquisition route.
