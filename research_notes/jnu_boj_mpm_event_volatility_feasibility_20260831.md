# JNU V2.2 — BOJ MPM Event Volatility Feasibility Review

Date: 2026-08-31

## Disposition

**BLOCKED_ON_INTRADAY_OUTCOME_DATA**

This is a source/data-feasibility disposition only. No outcome test was run, no parameter was fitted, and no directional claim is admitted.

## Direct evidence

Finta (2021), *Japanese monetary policy and its impact on stock market implied volatility during pleasant and unpleasant weather*, Pacific-Basin Finance Journal 67, 101562, DOI 10.1016/j.pacfin.2021.101562, directly studies BOJ Monetary Policy Meeting releases and intraday Nikkei 225 VI / Nikkei 225 VI futures. The reported release-time response is measured over minutes, so a daily-only implementation would not be a faithful Generation-1 confirmation.

## Event timestamp source

The Bank of Japan official MPM archive is suitable for point-in-time event timing. BOJ states that decisions are announced immediately after MPMs, and historical statement pages expose exact release dates/times (for example, 2025-05-01 at 12:02 JST; older annual index pages also list announcement times). This makes the event-side timestamp provenance executable without a paid calendar vendor.

## Outcome-data audit

Nikkei's public Nikkei 225 VI page is real-time and provides free CSV history only at daily frequency for a limited recent window. Nikkei's data-provision documentation states that the public site provides three years of daily index values and ten years monthly, while more extensive/tick data belongs to paid services. That is insufficient to reproduce or independently confirm the minute-scale release effect in Finta (2021).

The alternative of measuring BOJ release-time realized volatility directly in JNU/Nikkei 225 futures would require approved true OSE intraday data. Under current governance, the available personally licensed 225Labo raw data is local-only and has not yet been made accessible to the cloud research runner. Proxy index intraday data may not be promoted as true-JNU evidence.

## Governance consequence

- Do not open a formal statistical family yet.
- Do not replace the minute-scale target with daily Nikkei VI merely because daily data are free.
- Do not infer release timestamps from post-release market moves.
- Do not use VIX/SKEW as a substitute for Nikkei 225 VI.
- Revisit only when either (a) approved intraday Nikkei 225 VI/VI-futures history is available, or (b) approved true OSE/JNU intraday data is available and a separate preregistration freezes a realized-volatility target before outcome inspection.

## Sources

- BOJ MPM framework and official archives: https://www.boj.or.jp/en/mopo/mpmsche_minu/ and https://www.boj.or.jp/en/mopo/mpmdeci/
- Finta (2021) DOI: https://doi.org/10.1016/j.pacfin.2021.101562
- Nikkei 225 VI profile: https://indexes.nikkei.co.jp/en/nkave/index/profile?idx=nk225vi
- Nikkei index data provision: https://indexes.nikkei.co.jp/nkave/data/index.en.html
