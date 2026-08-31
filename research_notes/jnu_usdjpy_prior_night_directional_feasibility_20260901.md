# JNU directional candidate — prior-night USD/JPY reversal

Date: 2026-09-01

## Candidate

`PRIOR_NIGHT_USDJPY_TO_JNU_DAY_G1`

## Direct Nikkei/OSE evidence

Kiyotaka Satoyoshi, *Analysis of Price Fluctuations in the Nikkei 225 Futures Market: Night Session and Day Session*, OSE/JPX Futures & Options Report, September 2018.

The study uses OSE Nikkei 225 futures near-month daily OHLC, NY Dow and USD/JPY. Its sample begins after the July 2016 night-session extension and ends 2018-07-31.

For the Nikkei 225 futures **day-session return**, the lagged overnight USD/JPY change `EX_R(-1)` has a statistically significant **negative** coefficient: -0.264 with Newey-West t=-2.637. The paper interprets this as: when the yen strengthens overnight the following Nikkei futures day session tends to rise, and when the yen weakens overnight the following day session tends to fall. This is known before the OSE day open and is therefore causal for a directional information test.

This is substantively different from the terminal `OVERNIGHT_OVERREACTION_TRUE_JNU_G1`: that failed family used the futures' own previous-close/current-open return as predictor. This candidate uses a separate external market (USD/JPY) measured before the Japanese day session.

## Rights-clean/no-extra-cost input path

The paper's overnight FX variable uses:
- BOJ Tokyo-market USD/JPY spot at **17:00 JST**; BOJ official daily series `FM08'FXERD04`, available from 1998 onward.
- Federal Reserve H.10 Japanese-yen/USD noon buying rate in New York; FRED series `DEXJPUS`, available from 1971 onward.

Both are public official daily series. The target OSE Mini/JNU day return will be derived locally from personally licensed 225Labo raw, with only non-reconstructive daily sufficient statistics persisted to GitHub.

## Holdout design

The published study sample ends **2018-07-31**. To avoid reproducing the original in-sample result:
- Stage A: OSE Nikkei 225 Mini from **2018-08-01 through 2023-07-21** only.
- Stage B: exact OSE Nikkei 225 Micro (JNU) from **2023-07-24 onward**, only if Stage A passes.

## Candidate translation

For each OSE day-session trading date D:
1. Let t be the latest BOJ Tokyo business-date strictly before D for which both official FX observations exist on the same calendar date.
2. `FX_OVERNIGHT_t = log(Fed_H10_noon_NY_t / BOJ_17JST_t)` in yen per USD.
3. The paper's expected relation is negative, therefore fixed signal for day D is `-sign(FX_OVERNIGHT_t)`.
4. Target return is the OSE day-session open-to-close log return on D.
5. Primary daily signal payoff is `signal * target_return`.

No threshold, magnitude bucket, regime filter, night-session return, NY Dow input, HAR-RSV state or BOJ event state is added in G1.

## Why this is eligible to open

- direct OSE Nikkei 225 futures evidence;
- predictor is causal before OSE day open;
- mechanism/predictor is independent from the three recently failed directional families;
- official/free FX inputs exist;
- a clean post-paper Mini holdout exists before exact-JNU Micro confirmation;
- no parameter/horizon search is needed.
