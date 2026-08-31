# JNU directional literature screen — post-publication MACD holdout

Date: 2026-09-01

## Selected formal family

**MACD_4223_POST_PUBLICATION_TRUE_JNU_G1**

Direct Nikkei-futures evidence:
- Kang (2021), JRFM, DOI 10.3390/jrfm14010037, uses daily closing values of near-maturity Nikkei 225 futures from 2011-01-04 through 2019-12-30 and reports that the traditional MACD(12,26,9) performs poorly while an optimized example MACD(4,22,3) earns materially higher positive returns.
- Kang (2022), IJFR, DOI 10.5430/ijfr.v13n3p1, extends the Nikkei 225 futures parameter-stability analysis through 2021 and explicitly considers 2020-2021 pandemic performance.
- Because those studies include data through 2021, G1 will use only a post-publication Mini holdout beginning 2022-08-01, then exact JNU Micro confirmation.

Overfit control:
- The original 4/22/3 parameters came from a large external parameter search, so they are treated only as an externally specified hypothesis.
- G1 tests exactly one MACD parameter tuple: (4,22,3).
- No parameter ranges, modified false-signal filters, one-day holding variants, zero-crossover variants, or optimization are allowed.
- The traditional MACD(12,26,9) may be reported only as a diagnostic negative control and has no promotion power.

Translation:
- Use historical OSE day-session final close of the center/near contract.
- Compute EMA4, EMA22, MACD=EMA4-EMA22, signal=EMA3(MACD), histogram=MACD-signal.
- At day t close, position for t->t+1 is sign(histogram_t).
- Primary payoff is position_t * log(close_{t+1}/close_t).
- Zero histogram => flat/abstain.
- Primary gate is post-publication predictive information, not a full executable strategy; transaction costs are downstream.
