# JNU directional literature screen — intraday momentum / mean reversion

Date: 2026-08-31

## Selected next formal family

**INTRADAY_MOMENTUM_REVERSION_TRUE_JNU_G1**

Direct evidence:
- Ke Peng & Shiyun Wang (2008), *The Momentum and Mean Reversion of Nikkei Index Futures: A Markov Chain Analysis*, World Scientific, DOI 10.1142/9789812791696_0012.
- The paper reports significant **1-minute return momentum** and significant **10-minute return mean reversion** in Nikkei index futures, with the switching pattern robust to intraday seasonality.
- The authors discuss large limit orders and bid-ask effects as possible mechanisms. Therefore G1 is only an information/predictability gate; execution-cost and microstructure robustness remain mandatory downstream.

Why selected:
1. Direct Nikkei-futures evidence.
2. Exact horizons are supplied by literature rather than searched after outcomes.
3. Existing personally licensed OSE Mini/JNU 1-minute data are sufficient; no new paid/order-book source is needed.
4. The family can be tested with non-overlapping time periods: pre-Micro Mini Stage A, then exact JNU Micro Stage B.

Why other screened directions are not prioritized:
- Expiration/SQ evidence is mixed; older Nikkei evidence includes no significant expiration-day effect, so no directional SQ family is opened from the current evidence set.
- BOJ ETF anticipation evidence is primarily volume/liquidity rather than price adjustment and has weaker forward relevance after the BOJ framework change.
- Order imbalance remains blocked because OHLCV cannot substitute for signed trades/limit-order imbalance/spread data.
- The prior-SPX FIRST/LAST30 true-JNU family is already terminally rejected and cannot be rescued.

## G1 translation

The original Markov-chain result is translated into a strict OOS sign/return information gate rather than copied as an in-sample significance test.

- H1: adjacent 1-minute day-session returns exhibit continuation. A fixed momentum signal `sign(r[t-1])` should have positive next-return signal payoff and >50% nonzero-target directional accuracy.
- H2: adjacent **non-overlapping 10-minute** day-session returns exhibit reversal. A fixed reversal signal `-sign(R10[t-1])` should have positive next-block signal payoff and >50% nonzero-target directional accuracy.
- No cross-session returns.
- Historical OSE day-session segments are used; pre-2011 lunch breaks split the sequence.
- Zero predecessor returns are abstentions; zero target returns are excluded only from sign-accuracy denominator, not from payoff.
- Primary inference is day-level bootstrap of equal-weight daily mean signal payoff.
- H1 and H2 form one family and are Holm-corrected.
- Stage A uses OSE Mini dates before JNU Micro launch; Stage B uses exact JNU Micro from 2023-07-24 onward.
