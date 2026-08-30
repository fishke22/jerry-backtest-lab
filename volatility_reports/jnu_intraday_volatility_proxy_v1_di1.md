# JNU Intraday Volatility Method Proxy — jnu_intraday_volatility_proxy_v1_di1

- Status: **METHOD_PROXY_ONLY**
- OOS days: 1524 (2013-01-22 → 2018-12-31)
- Best QLIKE: **HAR_LEVERAGE**
- Best MSE: **HAR_LEVERAGE**
- Any proxy-method pass: **True**

## Losses
- HAR_RV: QLIKE=-8.9827173, MSE=1.626586e-08
- HAR_LEVERAGE: QLIKE=-8.9888194, MSE=1.62313e-08
- HAR_RSV: QLIKE=-8.9839203, MSE=1.6232881e-08

## Incremental tests vs HAR_RV
- HAR_LEVERAGE: QLIKE Δ=0.0061021223, MSE Δ=3.4559584e-11, Pboot(QLIKE>0)=0.871, Pboot(MSE>0)=0.657, PASS=False
  - 2011_2014: n=498, QLIKE Δ=0.001900094568059267, MSE Δ=5.869090576234195e-11
  - 2015_2018: n=1026, QLIKE Δ=0.008141703023930778, MSE Δ=2.2846720139546e-11
- HAR_RSV: QLIKE Δ=0.0012030168, MSE Δ=3.2978349e-11, Pboot(QLIKE>0)=0.683, Pboot(MSE>0)=0.959, PASS=True
  - 2011_2014: n=498, QLIKE Δ=-0.010803312369980193, MSE Δ=5.844817242401494e-12
  - 2015_2018: n=1026, QLIKE Δ=0.007030650325395889, MSE Δ=4.6148426009575494e-11

## Guardrail
- This is a Nikkei index-proxy methodology test, not OSE/JNU validation.
- Session, 5-minute sampling, HAR windows and model family were preregistered before results.
- No failed model may be rescued by changing windows on this sample.
- Formal JNU use requires the same frozen method on approved OSE/JNU intraday data.
