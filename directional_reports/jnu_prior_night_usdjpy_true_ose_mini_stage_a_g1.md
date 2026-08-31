# Prior-night USDJPY to OSE Mini day return — Stage A G1

- Overall status: **TRUE_OSE_MINI_PRIOR_NIGHT_USDJPY_STAGE_A_FAIL**
- Usable post-paper holdout days: **1,223** (2018-08-01 through 2023-07-21)
- Mean daily signal payoff: **-0.0004335029718195796**
- Directional accuracy: **47.3906%**
- Bootstrap P(mean payoff > 0): **0.0304**
- Bootstrap 95% CI: **[-0.0008662919618224796, 0.0000230129311746264]**
- Diagnostic OLS slope day return on prior-night FX change: **+0.03685914294781518**
- Valid workflow run: **33447920715**
- Artifact: **9778689265**

The direct 2018 JPX/OSE study reported a significant negative relationship between prior-night USD/JPY change and the following Nikkei 225 futures day-session return. In this strict post-paper OSE Mini holdout the relationship does not replicate: the diagnostic slope changes sign, the fixed literature-direction signal loses on average, and directional accuracy is below 50%.

The preregistered Stage A therefore fails. Exact-JNU Micro Stage B is prohibited. The family may not be rescued by changing FX measurement times, flipping the sign, using a different target session, weakening the threshold, or adding cross-market/risk filters.
