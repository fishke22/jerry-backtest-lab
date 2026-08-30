# JNU Intraday Path Proxy G0 — jnu_intraday_path_proxy_g0_v1

- Status: **PROXY_METHOD_SCREEN_ONLY**
- Derived panel days: 713
- Family PASS: **False**

## Frozen target tests
- first30_ret: beta_US=-0.028619521, expected=-1, MSE Δ=-6.8518063e-08, Pboot>0=0.139, hit Δ=-0.652pp, recent beta=-0.028619521, PASS=False
- last30_ret: beta_US=-0.00044220021, expected=+1, MSE Δ=3.5802904e-08, Pboot>0=0.618, hit Δ=1.087pp, recent beta=-0.00044220021, PASS=False

## Guardrails
- This is an index-proxy methodology screen, not JNU/OSE validation.
- The prior U.S. session is selected strictly by completion timestamp before Japan open.
- FIRST/LAST 30-minute windows are frozen from the 2026 direct Nikkei-futures evidence.
- No window, predictor, or sign may be changed to rescue a failure on this sample.
