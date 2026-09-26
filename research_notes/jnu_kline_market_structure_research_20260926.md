# JNU K-line / Market-Structure Research — 2026-09-26

Status: **FRAMEWORK GAP FOUND AND CORRECTED / NO NEW DIRECTIONAL VOTE**

## Why K-line analysis matters

A K-line is useful because it compresses path information into open, high, low and close. For JNU, however, the useful information is not the visual pattern name by itself. The useful information is:

- where the bar occurs relative to prior value/range/VWAP;
- how large the body/range/wicks are relative to current volatility;
- whether the move occurs in day/night/open/event liquidity;
- whether volume/participation confirms the move;
- whether price merely touched, broke, or was accepted beyond a structural level;
- whether lower and higher timeframes agree.

Traditional named candlestick patterns have mixed out-of-sample evidence, so JNU Research will not create a candlestick-pattern directional vote.

## Missing framework item discovered

The formal v1.9 framework contained `volume distribution`, `VWAP reclaim/loss`, and `higher lows/lower highs`, but the repository did not explicitly encode:

- trend versus box/balance structure;
- Volume/Price Profile;
- POC / VAH / VAL / HVN / LVN;
- Touch != Break != Acceptance;
- false break/rejection;
- value/box migration.

These were previously required by the user's JNU analysis method and are now restored as an explicit mandatory extension.

## Added modules

### 1. Auction Profile / Acceptance Structure

Treat POC/Value Area/HVN/LVN as locations, not automatic signals.

State:
- current balance/box versus trend;
- value migration;
- touch, break, acceptance or rejection;
- false breakout/re-entry;
- new-box migration only after sustained acceptance.

True Volume Profile requires real volume-at-price/tick data. OHLC-reconstructed profile is a proxy and must be labeled.

### 2. Opening Range / Initial Balance

Opening location alone is insufficient. Record the actual opening range and whether the first break is accepted or rejected.

Index-futures research shows the opening/closing of the underlying cash market concentrates trading volume and return fluctuations, and ORB-style information can be useful. This is not yet JNU-specific validated alpha.

### 3. Multi-timeframe Normalized Bar State

Do not say only “long lower wick” or “large bullish candle.”

Measure:
- body/range;
- upper/lower wick fractions;
- CLV;
- ATR/RV-normalized range;
- time-of-day normalized volume;
- compression/expansion;
- inside/outside range;
- 5m/15m/60m/session/daily agreement.

### 4. Signed Semivariance / Jump Risk

Separate upside/downside realized variation and signed jumps when intraday data permit.

Use only for:
- volatility/risk state;
- confidence caps;
- stop/target scaling;
- event-risk interpretation.

It is not an additional direction vote.

## Governance

These additions do not alter the four directional blocks and do not rescue any terminal-failed trend/breakout family.

Opening-range and acceptance features remain path/context evidence until direct OSE/JNU OOS and forward validation exists.

Named candlestick labels are auxiliary descriptions only.
