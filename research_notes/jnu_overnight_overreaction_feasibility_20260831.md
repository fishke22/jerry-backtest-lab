# JNU directional literature screen — overnight overreaction

Date: 2026-08-31

## Selected next formal family

**OVERNIGHT_OVERREACTION_TRUE_JNU_G1**

Direct evidence:
- Kotaro Miwa (2019), *Trading hours extension and intraday price behavior*, International Review of Economics & Finance 64, 572-585, DOI 10.1016/j.iref.2019.07.007.
- The study uses OSE Nikkei 225 futures and TOPIX futures, sample January 2002 through December 2015.
- Its core intraday-overreaction result is a negative association between the overnight return (previous regular-session close to current regular-session open) and the subsequent morning intraday return.
- The study also reports that night-session returns are negatively associated with subsequent intraday returns.
- G1 tests only the simplest core overnight-to-morning reversal. Night-session decomposition is diagnostic only and cannot rescue G1.

Why selected:
1. Direct OSE Nikkei 225 futures evidence.
2. Requires only existing Mini/JNU 1-minute OHLCV.
3. The literature sample ends in 2015, allowing a clean post-study true-OSE Mini holdout from 2016 onward, followed by exact-JNU Micro confirmation.
4. No new paid/order-book/external market source is needed.

## Translation

- Overnight return = log(current regular-session opening price / previous trading-day regular-session closing price).
- Morning return = log(price after the first 120 elapsed active day-session minutes / current regular-session opening price).
- Fixed signal = -sign(overnight return).
- Primary daily effect = signal * morning return.
- Expected effect > 0 and nonzero-target directional accuracy > 50%.
- The 120-minute elapsed window preserves the original paper's 09:00-to-11:00 two-hour concept after the OSE regular open moved to 08:45.
- Stage A is deliberately post-literature-sample: 2016-01-04 through 2023-07-21 OSE Mini.
- Stage B is exact JNU Micro from 2023-07-24 onward.
