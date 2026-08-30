# JNU V2.2 Evidence-First Target Architecture

Status: research target, not yet validated for live trading.

## Output model

The framework should not emit one opaque bullish/bearish score. It should emit three separate outputs:

1. **Direction**
   - calibrated probability of up / down over the relevant horizon;
   - evaluated with Brier score, log loss, calibration and realized EV, not raw accuracy alone.

2. **Risk / range**
   - expected volatility and plausible range;
   - event/jump-risk state;
   - used for sizing, stop distance and whether an apparent directional edge is economically tradable.

3. **Actionability / confidence**
   - TRADE / REDUCE_SIZE / NO_TRADE;
   - confidence must fall when major evidence layers conflict, source quality is stale, or an event regime is outside validated history.

## Evidence layers

### A. Data integrity and causal timing
All features must carry source time, first-known time, session availability and freshness. No same-day external close may predict an already completed Japanese session.

### B. Dynamic price-discovery leadership
Weights depend on which venue/session is actively discovering price:
- OSE Nikkei futures;
- Japanese cash Nikkei/TOPIX;
- US/CME futures and US cash;
- other Nikkei-linked futures when data is available.

No permanent equal-weight cross-market vote.

### C. Volatility / tail-risk state
Use long-memory and asymmetry when the required intraday/realized-volatility data is available. Daily-close-only approximations that fail information tests are not promoted.

### D. Conditional FX/rates state
USDJPY and rates are conditional states with lag/regime checks. No universal rule such as "weaker yen always means Nikkei up."

### E. Global / overnight risk state
US information matters, but its weight depends on trading timezone/session and information leadership. A rejected simple majority-vote model must not be resurrected.

### F. News / event / sentiment state
Category-aware, multilingual, deduplicated and time-decayed. Treat news first as volatility/event/confidence information. Direct directional use requires its own OOS evidence.

### G. Intraday market structure
When true intraday futures data is available:
- day/night path;
- OR15;
- VWAP;
- POC/VAH/VAL;
- volume/RVOL;
- prior/session highs/lows/closes;
- CLV and repair efficiency;
- basis/roll/OI where valid.

### H. Event regime
BOJ/FOMC and major scheduled macro releases are separate regimes. The framework may reduce size or abstain rather than force a direction.

### I. Decision fusion
Fuse only validated or explicitly research-status layers. Use calibrated probabilities / conditional EV rather than subjective score addition.

## Promotion rule

A factor can affect live analysis only according to its research status:
- VALIDATED: may influence calibrated decision output.
- CONDITIONAL: only in the validated regime.
- RESEARCH_ONLY: may be displayed as context but cannot raise confidence.
- REJECTED: must not be used to justify a trade.

No literature paper, backtest profit, or second-engine replay alone is sufficient for VALIDATED status.
