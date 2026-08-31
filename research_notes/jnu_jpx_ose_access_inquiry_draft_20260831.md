# Draft — JPX/OSE historical tick-data eligibility inquiry (2026-08-31)

Status: **PREPARED_NOT_SUBMITTED**

Purpose: resolve the highest-priority no-extra-cost true-OSE data-access path before falling back to the personally licensed local 225Labo dataset. This draft must not be sent using guessed identity, company affiliation, or eligibility claims.

Official contact identified on JPX OSE market-information pages: `md@jpx.co.jp` (JPX Market Innovation & Research, Inc. Client Services / contractor for OSE market information).

## Proposed inquiry

Subject: Eligibility and permitted research use of OSE historical tick-data trial for Nikkei 225 futures

Dear JPX/OSE Client Services,

I am conducting non-commercial research and backtesting on Nikkei 225 futures market data and would like to clarify eligibility and permitted use of the OSE historical tick-data route described on the JPX Historical Data page under “Sample transaction data for examining trading methodology.”

Could you please confirm the following before any application or data acquisition?

1. **Individual eligibility** — Can an individual/private researcher apply, or is the historical-data/free-trial route limited to companies or prospective OSE trading participants?
2. **Products** — Can the trial or methodology-examination dataset include Nikkei 225 mini and/or Nikkei 225 micro futures?
3. **Granularity** — Is tick data available, and can one-minute OHLC/volume data also be provided where appropriate?
4. **Historical period** — What is the longest historical period that may be supplied for Nikkei 225 mini and Nikkei 225 micro under this route?
5. **Research purpose** — Is internal non-commercial quantitative research/backtesting of volatility forecasting, realized volatility/semivariance, and intraday market behaviour an acceptable purpose?
6. **Retention** — May the raw data be retained locally after the trial/application period for reproducibility of the approved research, or must it be deleted at the end of the permitted period?
7. **Processing location** — Must all raw-data processing remain on a local/private computer, or is private cloud computation permitted?
8. **Derived outputs** — May non-reconstructable derived features, source hashes, provenance metadata, statistical diagnostics and aggregate research results be stored in a private cloud/Git repository, provided no raw OSE market data are redistributed?
9. **Publication / sharing** — What restrictions apply to publishing only aggregate/non-reconstructable research results derived from the data?
10. **Application path** — If an individual is eligible, which application form/process should be used for historical data supplied specifically for trading-methodology examination?

The intended use is research only. No raw OSE market data would be publicly redistributed, and no automated trading or broker connection is part of this data-access request.

Thank you for your guidance.

Kind regards,
[USER NAME / AFFILIATION IF APPLICABLE]

## Internal handling rules

- Do not send until the user explicitly asks to submit/contact JPX and sender identity/affiliation requirements are known.
- Do not state or imply company status if the user is applying as an individual.
- A positive reply must still be checked for product/date coverage, retention, processing and derived-output rights before any acquisition.
- Raw OSE trial data must not be uploaded to GitHub/cloud unless the written terms explicitly permit that storage.
- If individual eligibility is denied or the history is inadequate, revert to the local-only 225Labo true-OSE path for HAR-RSV Stage A rather than opening another proxy rescue family.
