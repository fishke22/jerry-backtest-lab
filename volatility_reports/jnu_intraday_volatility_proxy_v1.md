# JNU Intraday Volatility Method Proxy — jnu_intraday_volatility_proxy_v1

- Status: **METHOD_PROXY_ONLY**
- OOS days: 1524 (2013-01-22 → 2018-12-31)
- Best QLIKE: **HAR_LEVERAGE**
- Best MSE: **HAR_LEVERAGE**
- Any proxy-method pass: **False**

## Losses
- HAR_RV: QLIKE=-8.9840114, MSE=1.6251716e-08
- HAR_LEVERAGE: QLIKE=-8.9902756, MSE=1.6217286e-08
- HAR_RSV: QLIKE=-8.9849312, MSE=1.6223882e-08

## Incremental tests vs HAR_RV
- HAR_LEVERAGE: QLIKE Δ=0.0062641741, MSE Δ=3.442968e-11, Pboot(QLIKE>0)=0.878, Pboot(MSE>0)=0.655, PASS=False
  - 2011_2014: n=498, QLIKE Δ=0.0021297080242139027, MSE Δ=6.017679814430175e-11
  - 2015_2018: n=1026, QLIKE Δ=0.008270961685565003, MSE Δ=2.193254137273975e-11
- HAR_RSV: QLIKE Δ=0.00091979382, MSE Δ=2.7833592e-11, Pboot(QLIKE>0)=0.655, Pboot(MSE>0)=0.934, PASS=False
  - 2011_2014: n=498, QLIKE Δ=-0.010479904781972162, MSE Δ=-2.0898366114976566e-12
  - 2015_2018: n=1026, QLIKE Δ=0.00645298086317699, MSE Δ=4.2357829892824235e-11

## Guardrail
- This is a Nikkei index-proxy methodology test, not OSE/JNU validation.
- Session, 5-minute sampling, HAR windows and model family were preregistered before results.
- No failed model may be rescued by changing windows on this sample.
- Formal JNU use requires the same frozen method on approved OSE/JNU intraday data.
