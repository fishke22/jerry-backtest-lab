# JNU Precision-Feature Research Feasibility — 2026-09-26

Status: **PREREGISTERED / DATA-AVAILABILITY CLASSIFIED / NO NEW DIRECTIONAL VOTE**

Authoritative framework remains `config/jnu_operational_framework_current_v1_9.json`.
Mandatory precision-analysis companion memory is `config/jnu_cross_session_precision_analysis_memory_v1.json`.
Frozen research specification is `config/jnu_precision_feature_research_prereg_v1.json`.

## Research conclusions

### 1. Nikkei breadth / concentration — operational context available now

Nikkei Indexes Daily Summary exposes daily advance/decline counts, top component weights, sector weights and sector contribution. This is sufficient for contemporaneous JNU context and evidence-quality checks.

It is **not** sufficient by itself for a clean long historical backtest unless a rights-clean, point-in-time bulk history is assembled. Do not reconstruct old breadth using today's constituent list or weights.

Official source:
- https://indexes.nikkei.co.jp/en/nkave/archives/summary

Role:
- context / evidence quality;
- no additional directional vote.

### 2. Nikkei 225 VI — official daily history exists

Nikkei Indexes publishes Nikkei 225 VI and a Daily Data CSV. The index is based on OSE Nikkei futures/options and represents approximately 30-day expected volatility.

Official sources:
- https://indexes.nikkei.co.jp/en/nkave/index/profile?idx=nk225vi
- https://indexes.nikkei.co.jp/nkave/historical/nikkei_stock_average_vi_daily_en.csv

Research use frozen in preregistration:
- VI level percentile and daily change versus subsequent realized JNU volatility;
- price/VI divergence as a risk-state classifier;
- incremental information over VIX-only context.

Current role:
- volatility/risk/confidence modifier;
- not directional alpha.

Licensing note:
Nikkei Indexes states that business/non-display use and redistribution may require permission. Do not assume bulk historical data can be republished or embedded in a public repository.

### 3. JGB yield curve — official historical daily data exists

Japan Ministry of Finance publishes historical constant-maturity JGB rates, including an all-history CSV.

Official sources:
- https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/index.htm
- https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv

Research use frozen in preregistration:
- 2Y / 10Y / 30Y changes;
- 2s10s and 10s30s curve changes;
- BOJ-event versus non-event separation;
- no causal claim from daily rates alone.

Current role:
- event/cross-market refinement;
- not an independent vote.

### 4. Macro surprise — actual data is public, historical PIT consensus remains a blocker

Official releases can provide actual values, but historical pre-release consensus must be point-in-time correct. Backfilled consensus or post-release revisions are prohibited.

Status:
- CONDITIONAL / BLOCKED for formal historical surprise backtest until a rights-clean PIT consensus history is available.

### 5. Order flow / microprice — research mechanism is plausible, data gate remains real

Peer-reviewed Nikkei 225 futures work supports order-imbalance research. Japan FSA analytical work using granular Nikkei futures data also supports studying liquidity withdrawal, concentration and quote/depth behavior.

However, JPX complete derivatives four-price, one-minute and tick history is a charged data product, and historical tick trial access is conditional.

Official / research sources:
- https://www.jpx.co.jp/english/markets/paid-info-derivatives/historical/
- https://www.jpx.co.jp/english/markets/paid-info-derivatives/sample/
- https://www.fsa.go.jp/en/about/fsaanalyticalnotes/
- https://www.tandfonline.com/doi/abs/10.1080/00036840902881819

Status:
- UNAVAILABLE for formal historical OSE Micro/Mini order-book validation without authorized data;
- do not synthesize or infer order flow from ordinary OHLC.

### 6. MOF FX intervention — official regime labels available

Japan Ministry of Finance publishes official foreign-exchange intervention records.

Official source:
- https://www.mof.go.jp/english/policy/international_policy/reference/feio/index.html

Current role:
- event-risk modifier;
- confirmed intervention is a distinct regime from ordinary USDJPY volatility.

### 7. Session/liquidity normalization — operationally required, exact historical validation data-dependent

Time-of-day state must distinguish day/night, opening/closing auction, Japanese cash-session status and event windows.

Current role:
- signal normalization;
- exact Micro minute/tick historical validation remains conditional on authorized history.

## Lower-wick candidate

`LOWER_WICK_FAILED_BREAKDOWN_RECLAIM_CONFIRMATION` remains **RESEARCH_CANDIDATE_NOT_A_DIRECTIONAL_VOTE**.

Frozen definition:
- lower shadow >= 2 x candle body;
- lower shadow >= 50% of full range;
- signal-day low < previous-day low;
- signal-day close > previous-day close;
- confirmation only if next trading day trades above signal-day high.

Proxy evidence is exploratory only. No more threshold tuning is allowed.

Promotion requires:
1. true OSE Nikkei 225 mini individual-contract untouched OOS;
2. costs and roll governance;
3. incremental comparison versus generic prior-high breakout;
4. multiple-testing correction and confidence intervals;
5. exact Micro individual-month validation;
6. forward validation.

## Research boundary

There is no remaining research recommendation that can honestly be promoted to validated JNU directional alpha using currently available free evidence alone.

Future progress is data/evidence gated, not blocked by a missing idea:
- official VI/JGB/breadth/MOF inputs can improve context now;
- true order-flow and exact OSE OOS need authorized history;
- macro-surprise history needs PIT-safe consensus;
- directional promotion needs future OOS/forward evidence.

Do not create additional indicators merely to produce a signal.
