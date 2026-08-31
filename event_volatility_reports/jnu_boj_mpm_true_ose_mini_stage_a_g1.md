# BOJ MPM true-OSE Mini event-volatility Stage A G1

- Status: **TRUE_OSE_MINI_BOJ_EVENT_VOL_STAGE_A_PASS**
- Usable events: **170 / 170 timing-eligible**
- Mean log(EventRV/BaselineRV): **0.4450516453986761**
- Median log(EventRV/BaselineRV): **0.2951189323620672**
- Bootstrap P(mean effect > 0): **0.981**
- Bootstrap 95% CI: **[0.029547011546631502, 0.7571929210770287]**
- Valid workflow run: **33396821958**
- Artifact: **9759636087**

The preregistered Stage A gate passes. This is event/risk-state information only, not directional alpha. Exact JNU Micro Stage B is now permitted and must use the identical transform and thresholds without retuning.

## Data-integrity audit

Before statistical outcome inspection, DI1 corrected a legacy XLS parsing issue: 2012-2015 and other old annual workbooks split 1-minute history across multiple `1min*` sheets. The original adapter read only the first exact `1min` sheet when present. DI1 merged all 1-minute shards and restored the Stage-A data panel from 104/170 to **170/170** usable events. DI2 added generic manifest fields only. Neither revision changed event windows, thresholds, bootstrap settings, eligible dates, or the statistical hypothesis.
