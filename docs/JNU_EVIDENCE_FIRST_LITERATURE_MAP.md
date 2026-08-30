# JNU V2.2 Evidence-First Literature Map

Updated: 2026-08-30

## Objective

Improve the JNU research framework from prior published evidence before creating new parameter grids. No literature-backed idea is considered valid for JNU until it passes the project's own OOS / walk-forward / cost / overfit / forward-OOS gates.

## Evidence hierarchy

### Tier A — Direct Nikkei / Nikkei futures evidence

1. **Price discovery is not confined to the home cash market.**
   - Covrig, Ding & Low (2004): Nikkei futures contributed most price discovery, with SGX contributing materially despite lower volume.
   - Kao, Ho & Fung (2015): minute-by-minute US/Japan futures linkage is time-zone and trading-location dependent.
   - Qin, Green & Sirichand (2023): spot/futures leadership changed across regimes; foreign Nikkei futures retained cross-border leadership.

   **Framework implication:** Use a dynamic price-discovery/session layer. Do not use fixed equal weights for OSE, cash Nikkei, CME/US markets across all hours.

2. **Nikkei volatility has asymmetry / long memory and benefits from high-frequency information.**
   - Andersen, Bollerslev & Cai (2000): strong intraday periodicity and long-memory volatility in Japanese equities.
   - Asai & McAleer (2017): Nikkei 225 futures volatility forecasts improve when using underlying high-frequency information with asymmetric/long-memory volatility models.

   **Framework implication:** Volatility should be a state/risk variable with memory and asymmetry. A one-threshold high/low-vol directional rule is too crude.

3. **Global / US risk information matters for Japan.**
   - Andersen, Todorov & Ubukata (2021): US option-implied tail-risk contains forecasting information for Japanese excess returns and USDJPY.
   - Kao, Ho & Fung (2015): US/Japan futures information transmission changes across trading locations and time zones.

   **Framework implication:** Add a global-tail-risk / US-risk state separate from simple NQ direction.

4. **JPY–equity relation is meaningful but time-varying.**
   - Narayan, Devpura & Wang (2020): yen depreciation was associated with stronger Japanese equity returns, especially in the COVID regime.
   - Other Japanese FX-equity studies report time-varying / bidirectional relationships.

   **Framework implication:** USDJPY must be conditional on regime and lag structure. Never hard-code "yen weaker = Nikkei bullish" as a universal rule.

### Tier B — Direct Japanese news / sentiment evidence

5. **Japanese news sentiment contains information, but content and regime matter.**
   - Ishijima, Kazumi & Maeda (2015): a Nikkei-newspaper sentiment index had short-horizon predictive content for Japanese stock prices.
   - Du (2020): Nikkei reactions differ by news type and subperiod.
   - Feng, Fu & Shi (2022): news occurrence and sentiment, especially macro news, are linked to Japanese stock-return volatility states.
   - Nakayama & Yokouchi (2025): category-aware news indices improved predictive/trading performance relative to undifferentiated news treatment.
   - Smales (2026): for CME Nikkei futures, Japanese/English fundamental sentiment and US-local sentiment mattered differently across regimes/tails.

   **Framework implication:** Add news/sentiment as a **separate state layer**, not one scalar bullish/bearish vote. It should include category, language/source, novelty, surprise, intensity, recency and market regime.

6. **Policy uncertainty is more useful as a regime/risk factor than a fast entry signal.**
   - Chiang (2020): Japanese returns respond negatively to changes in policy uncertainty, with asymmetric and lagged effects.

   **Framework implication:** Japan/US policy uncertainty belongs in the slower background regime, not the 1-minute entry trigger.

### Tier C — Broad futures evidence, usable only as prior

7. **Time-series momentum is robust across diversified futures, but not guaranteed for one Nikkei contract.**
   - Moskowitz, Ooi & Pedersen (2012) find time-series momentum across 58 liquid futures.
   - Our Nikkei-only momentum candidate failed our own overfit gates.

   **Framework implication:** Do not resurrect the failed Nikkei momentum module simply because broad futures literature is positive.

8. **Volatility scaling is not automatically a free alpha source.**
   - Later OOS literature finds generic volatility-managed portfolios can fail in real time / after costs.

   **Framework implication:** Use volatility forecasts first for risk, confidence and position sizing; require separate proof before claiming return enhancement.

## Evidence-supported JNU framework layers

1. Dynamic price discovery / session leadership
2. Volatility and tail-risk state
3. Conditional USDJPY / rates state
4. US/global risk and overnight spillover
5. News / event / sentiment state
6. Existing intraday market structure (VWAP, POC/VAH/VAL, OR15, day/night path)
7. Conflict resolution / confidence calibration
8. Risk / execution constraints

## News layer design

Do **not** use:
- one LLM sentiment score,
- unweighted article counts,
- one-language-only news,
- same weight for scheduled and unscheduled news,
- same decay for all categories.

Pre-register these fields:
- event_time and first_seen_time
- source and language
- category: Japan macro/BOJ, Japan politics/policy, Nikkei constituents, US macro/Fed, US equity/semiconductor, FX/rates, geopolitics, energy/commodity
- sentiment polarity
- surprise vs prior expectation (when measurable)
- novelty / duplicate cluster
- source diversity
- intensity / article count
- recency decay
- affected session
- volatility-state interaction

Initial use: risk-state and confidence adjustment. Directional trading use requires separate OOS proof.

## Current research decision

No currently tested module is VALIDATED_JNU_MODULE.
- volatility_regime: QUARANTINE; promising structural evidence but failed DSR/Holm gates.
- cross_market_confirmation: rejected for extreme PBO.
- literature-backed Phase 4 candidates must be pre-registered before testing.


## 2026 direct intraday Nikkei-futures evidence

### Iwanaga (2026) — prior-day S&P 500 and Nikkei 225 futures intraday returns
- Paper: *How the prior day's S&P 500 returns influence the intraday returns of Nikkei 225 futures*
- DOI: `10.1016/j.finr.2026.100108`
- Status: open access / Finance Research Open.
- Direct implication for JNU: the prior U.S. equity return should **not** enter as a fixed all-session directional weight.
- Reported pattern: higher prior-day S&P 500 returns are associated with lower returns in the first 30 minutes of the Japanese session and higher returns in the last 30 minutes.
- Interpretation offered by the paper: temporary overreaction/reversal near the open versus rebalancing/intraday momentum toward the close; mechanisms are interpretive rather than directly proven.
- JNU research consequence:
  1. Pre-register `FIRST_30M` and `LAST_30M` as separate states.
  2. Test prior-U.S.-return interactions with those states, not a universal NQ/ES sign.
  3. No parameter search around 30 minutes in generation 1.
  4. Treat the paper as support for **Intraday Path / session conditioning**, not immediate trading authorization.


## Direct Japanese realized-volatility asymmetry evidence

### Maki & Ota (2020) — realized volatility asymmetry in Japanese futures and spot markets
- Paper: *The impacts of asymmetry on modeling and forecasting realized volatility in Japanese stock markets*
- DOI: `10.48550/arXiv.2006.00158`
- Market scope: Japanese spot market and Nikkei 225 futures.
- Models explicitly compared include HAR variants using positive/negative realized semivariance, asymmetric jumps, and leverage effects.
- Reported evidence: leverage effects are present in both spot and futures markets; realized semivariance is materially useful in modeling realized volatility, although performance depends on model specification.
- JNU research consequence:
  1. The existing DI1 HAR-RSV proxy pass has direct Japanese-futures literature support and is therefore higher priority than inventing a new volatility family.
  2. Keep HAR-RSV frozen for true-JNU confirmation; do not expand the parameter grid merely because other asymmetric HAR variants exist.
  3. HAR leverage/jump variants remain separate future families and cannot be added to rescue HAR-RSV if true-JNU confirmation fails.
  4. Volatility remains a risk/sizing state first, not automatic directional alpha.


## 2026 direct Nikkei-futures language/source sentiment evidence

### Smales (2026) — When news travels
- Paper: *When news travels: The role of sentiment in CME Nikkei futures returns*
- DOI: `10.1016/j.ribaf.2025.103223`
- Market: CME Nikkei futures (NIY), sample Jan-2003 to Sep-2020.
- Direct finding: Japanese-underlying "fundamental sentiment" is more important than U.S.-local sentiment overall; Japanese- versus English-language Japanese-stock news matters differently across regimes.
- The paper also reports sentiment-volatility asymmetry: positive fundamental/local sentiment is associated with lower volatility and negative sentiment with higher volatility.
- Critical data caveat: the original study uses Thomson Reuters News Analytics (TRNA), and the paper states the news data cannot be shared.
- JNU consequence:
  1. Language/source separation is academically justified as a new family after the broad-news screen became data-inconclusive.
  2. GDELT `sourcelang` is a proxy for publication language, not a replication of TRNA sentiment analytics.
  3. Any GDELT pass must be described as independent proxy evidence only.
  4. G1 remains a volatility/event-state test; directional sentiment trading is a separate family.


## 2026 BOJ policy-anticipation microstructure evidence

### Market anticipation and intraday trading: Evidence from BOJ ETF purchases (2026)
- Paper: *Market anticipation and intraday trading: Evidence from BOJ ETF purchases*
- Journal: Finance Research Letters, 2026, 109421.
- Direct market scope: Nikkei 225 futures on Osaka and Singapore venues.
- Reported mechanism: when BOJ ETF intervention was anticipated, Nikkei futures trading volume rose during the lunch period while prices remained comparatively stable; similar volume-price decoupling appeared in OSE and SGX.
- JNU consequence:
  1. Policy/event information can enter through liquidity and execution intensity without an immediate directional price move.
  2. RVOL/liquidity/session features should therefore remain execution/state variables unless separately validated for direction.
  3. Do not translate a BOJ-policy headline into an automatic long/short vote.
  4. The historical BOJ ETF-purchase mechanism is not treated as a current standalone alpha family.
