# JNU Independent Directional Scout + Stage-4 Risk Translation Priority — 2026-09-01

## Governance outcome
- No new formal directional family opened.
- Five recent true-target directional failures remain terminal; no close variants are admissible.
- Decision engine remains NO_VALIDATED_DIRECTIONAL_EDGE.

## BOJ MPM DI3 integrity audit and reconfirmation
Three event-corpus records incorrectly used 08:50, the later Summary/Minutes publication time, instead of the policy-decision release time:
- 2024-07-31 -> 12:56 (BOJ official decision page)
- 2025-01-24 -> 12:23 (BOJ official decision page)
- 2026-06-16 -> 12:19 (BOJ official decision page)

The three records had therefore been excluded by the frozen same-session eligibility rule. DI3 corrected timestamps only; Stage A remained 170 events and Stage B increased from 22 to 25. The frozen exact-JNU Stage B was rerun without changing the event window, bootstrap, threshold or role.

DI3 Stage-B result:
- run: 33499625359
- artifact: 9797148545
- usable events: 25
- mean log(EventRV/BaselineRV): 1.596492392509979
- median: 1.6834848265376794
- bootstrap P(mean>0): 1.000
- 95% CI: [1.1365538431921822, 2.0633442915156213]
- status: PASS, risk/event information state only.

## Stage-4 priority
### 1. BOJ MPM new-entry blackout design
Why first: discrete official event state, low degrees of freedom, low turnover, exact-JNU event-volatility effect remains strong after DI3.

PIT constraint: exact Statement release time is unknown before the meeting ends. The BOJ release schedule lists the upcoming Statement time as undecided, so the Stage-3 release-minus-10-minute research window cannot be used directly as a live blackout start.

Timing-only operational diagnostic, with no price outcomes:
- regular/scheduled MPM releases 2016-2026, excluding clearly unscheduled 2020-03-16 and 2020-05-22 meetings
- n=84
- earliest=11:25 JST
- p05=11:39
- median=12:00
- p90=12:35
- latest=13:18

Design seed only, NOT preregistered:
- on scheduled MPM decision day, block NEW entries from 11:00 JST
- continue until 20 minutes after official policy-decision release is actually observed
- if the release is not observed, remain blacked out through day-session close
- do not force-close existing positions in the first translation
- no directional vote

### 2. HAR-RSV exposure-cap design
HAR-RSV has much longer evidence, but a continuous sizing translation has more researcher degrees of freedom. Exact-JNU Stage B passed under the frozen rule mainly through MSE (P=0.9685; QLIKE P=0.522). Keep the first translation to one exposure-cap mapping only and do not combine sizing, stops and confidence changes.

## Independent directional evidence scout
### US option-implied left-tail risk -> Japanese returns
Andersen, Todorov & Ubukata (2021), Journal of Econometrics, DOI 10.1016/j.jeconom.2020.07.005, reports that U.S. option-implied negative tail risk predicts Japanese excess returns while Japan-specific predictors are generally weak. This is substantively independent from MACD, prior-US intraday path, overnight overreaction, short-horizon momentum/reversion and USDJPY.

Disposition: potentially valuable but DATA_BLOCKED. No verified free/authorized rights-clean historical source currently reproduces the required tail-risk measure. VIX/SKEW substitution is prohibited.

### CFTC CME Nikkei positioning
CFTC publishes free Nikkei yen-denominated TFF/COT positioning. Data availability alone is insufficient: this scout did not find strong direct peer-reviewed evidence for a frozen positioning transform that predicts subsequent OSE/JNU returns.

Disposition: scouting only; no formal family.

### BOJ policy surprise direction
Literature supports contemporaneous asset-price responses to policy surprises, but this is not a clean pre-event directional predictor and surprise measures can require additional market-expectations data.

Disposition: no formal family.

### BOJ ETF purchase surprise
Open research reports large positive instantaneous Nikkei effects from unexpected BOJ purchases, while later OSE/SGX futures research finds anticipated purchases mainly affect trading volume rather than price. The purchase regime is historical and not a current directional family.

## Next gate
Do not open a new directional family. The next formal research action, if any, should be a single preregistered Stage-4 BOJ entry-blackout translation after its PIT detection and validation objective are frozen. HAR-RSV remains Stage-4 priority #2.
