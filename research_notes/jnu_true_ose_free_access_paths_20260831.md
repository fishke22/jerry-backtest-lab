# JNU / Nikkei true-venue free-access research — 2026-08-31

## Executive finding

The highest-value newly verified no-extra-cost path is an **official JPX/OSE free-trial/application route for historical tick data used to examine trading methodology**. This is materially different from a public proxy: if JPX approves Nikkei 225 mini/large historical data and the permitted use covers the frozen research, it could potentially supply true-OSE evidence for HAR-RSV Stage A and possibly the frozen intraday path family.

This is **not** an automatically downloadable free dataset. Approval, product/date coverage, retention, cloud-processing, derived-output and internal-use conditions must be confirmed before acquisition. No application has been submitted yet.

## JPX / OSE official evidence

- JPX Historical Data service states that OSE/TOCOM tick, one-minute OHLC and OHLC data are sold through J-Quants DataCube.
- JPX separately states under “Sample transaction data for examining trading methodology” that historical tick data **may be provided** to parties considering new participation in the OSE market if certain conditions are met.
- The general OSE market-information free-trial page says the trial is normally one month, for parties considering obtaining/using OSE market information, limited to internal usage before an Information Provision Agreement.
- The published operational process says an applicant is a company and asks for company/contact information, representative details, direct-user information when applicable, period, and other requested details; approval is by OSE.
- JPX Data Cloud price-list metadata confirms official historical availability for Nikkei 225 mini from 2006-09-01 and Nikkei 225 micro from 2023-05-29. These dates prove official granular history exists, but they do **not** prove the free-trial sample will include the same full coverage.

### Research classification

`JPX_OSE_HISTORICAL_FREE_TRIAL_APPLICATION = HIGHEST_PRIORITY_FREE_TRUE_OSE_APPLICATION_PATH`

Potential role if approved:
1. HAR-RSV true-OSE Stage A on Nikkei 225 mini/large.
2. Exact-product JNU micro Stage B if micro history is included and adequate.
3. Frozen true-OSE intraday-path test if minute/tick coverage is sufficient.

Forbidden before approval:
- assume eligibility;
- assume full 2006+ mini or 2023+ micro history will be free;
- upload raw trial data to public/cloud storage without explicit permission;
- treat sample access as redistribution rights.

## SGX historical tick lead

Open-source repositories document a legacy SGX endpoint family:

`https://links.sgx.com/1.0.0/derivatives-historical/{id}/WEBPXTICK_DT.zip`

The repositories describe daily tick archives plus `TickData_structure.dat`, `TC.txt`, and `TC_structure.dat`; one configuration maps an index to 2023-04-13 and records an earliest logical date of 2004-07-23. Another historical downloader says the useful required-format archive begins 2013-04-05.

This is a strong technical lead that historical SGX daily tick files existed and were downloadable. It is **not** sufficient legal authority for automated bulk acquisition today. SGX’s current Market Data Policy governs market-data usage and non-display usage; therefore no GitHub Actions scraper should be launched until current rights for historical website files and quantitative research are explicitly established.

Classification:

`SGX_WEBPXTICK_HISTORICAL_ENDPOINT_LEGACY = HIGH_VALUE_LEAD_NOT_YET_APPROVED_FOR_AUTOMATION`

## Commercial reference sources (not adopted)

- JPX Data Cloud: official exact OSE tick/1-minute data; paid.
- Portara/CQG: OSE Nikkei 225 mini intraday from 2006-07-18 and SGX Nikkei 225 intraday from 1991-04-26; free tier currently unavailable.
- Tick Data LLC: rich OSE/SGX futures history; commercial.

These sources prove the required historical datasets exist but remain outside the project’s no-paid-data policy unless separately authorized.

## Next recommended action

Prepare, but do not submit without user identity/eligibility details, an OSE/JPX inquiry requesting whether the historical-data free-trial path can cover:

- Nikkei 225 mini, preferably 2006+ or the longest permitted historical sample;
- Nikkei 225 micro, 2023+ if available;
- tick and/or one-minute OHLCV;
- research/backtesting of volatility forecasting and intraday methodology;
- local/internal processing with raw data retained privately;
- permission to store only non-reconstructable derived features, hashes, provenance and aggregate research results in a private cloud/GitHub repository.

Until that answer is obtained, the formal global blocker remains `TRUE_OSE_INTRADAY_DATA_ACCESS`.
