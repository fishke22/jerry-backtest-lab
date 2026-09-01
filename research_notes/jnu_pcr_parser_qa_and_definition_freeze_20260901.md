# PCR parser QA and pre-outcome definition freeze — 2026-09-01

- Frozen 9-date structural QA rerun: 9/9 PASS.
- Initial apparent 9/9 run is retained as engineering-ineligible because modern sparse rows could mis-map YYYYMM into Trading Volume.
- Integrity rerun classifies modern no-trade rows as volume zero and logs extraction mode.
- No directional return outcome was used.

## Frozen G1 information definition
- OSE total issue volume = Auction + J-NET.
- Near + second-near standard Nikkei 225 option maturities.
- Nearest OTM put/call based on same-day official Nikkei reference close.
- Daily ratio = 100 × selected put-volume sum / selected call-volume sum.
- Monthly PCR = arithmetic mean of the five daily ratios.
- If a required day's selected call-volume denominator is zero, that daily PCR is undefined and the month is unusable under G1.
- No farther-strike, fewer-day, ratio-of-sums, weekly-option, mini-option, or pseudocount rescue.

Current status: PARSER_QA_PASS_FULL_PANEL_FEASIBILITY_PENDING. No formal directional family is open.
