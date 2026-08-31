# True-JNU prior-SPX intraday path G1

Status: **REJECT_TRUE_JNU_CURRENT_SPEC**

- Exact-product JNU causal-aligned days: 796
- OOS per cell: 736 (2023-10-16 → 2026-08-31)
- H1 FIRST30: expected negative beta is present, but Pboot(MSE improvement>0)=0.84 < 0.95
- H2 LAST30: expected positive beta is present, but mean MSE improvement is negative and Pboot=0.454
- H3 state interaction: mean MSE improvement is negative and Pboot=0.354
- Holm family pass: **false**; the smallest one-sided p-value is 0.16 vs first Holm threshold 0.0333

The coefficient-sign pattern resembles the direct literature, but it does **not** clear the preregistered OOS information gate on exact-product JNU data.

This family is terminally rejected under its current specification. Forbidden rescue actions include changing the 30-minute windows, switching the U.S. predictor class, dropping H2/H3, adding technical indicators/regimes, or reopening another proxy variant.

Valid workflow run: **33391992462**; artifact **9757824371**.
