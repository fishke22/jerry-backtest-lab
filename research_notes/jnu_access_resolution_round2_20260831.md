# JNU true-venue access resolution — round 2 (2026-08-31)

## JPX/OSE official path

Current JPX Historical Data documentation states:
- OSE futures/options historical tick, one-minute OHLC, and OHLC data exist through J-Quants DataCube.
- Sample files are available through the Sample Data button on individual DataCube product pages.
- A separate free-trial path may provide historical OSE tick data for examining trading methodology if certain conditions are met.
- The official enquiry route is JPX Market Innovation & Research Client Services through the J-Quants DataCube contact form: https://dc.jpx-jquants.com/en/contact

The published free-trial operational process describes the applicant as a company and asks for company/representative information. Therefore retail-individual eligibility remains unresolved and must not be assumed.

The DataCube product page returned HTTP 403 to the current automated web retrieval environment. This is an access limitation of the current retrieval path, not evidence that the sample files do not exist. JPX's own historical-data page explicitly states they are available on product pages.

## SGX historical path

SGX Data Direct publishes a Market Data Policy effective 1 July 2026 governing display, non-display, redistribution and reporting. This means legacy public archive existence is not enough to authorize automated quantitative ingestion or cloud retention.

Current SGX rulebook material explicitly identifies Nikkei 225 Index Futures and Micro Nikkei 225 Index Futures; other rulebook material identifies Mini Nikkei 225 Index Futures. This confirms current SGX Nikkei product identity, but does not establish the legacy WEBPXTICK archive's historical contract codes.

The public repository `nicapos/SGX-data-project` documents daily downloads of `WEBPXTICK_DT`, `TickData_structure.dat`, `TC.txt`, and `TC_structure.dat`, with a default historical start date of 2004-07-23. It is technical evidence that the archive family existed, not current legal authority to bulk download.

## Current disposition

1. Do not start a new alpha family.
2. Do not scrape or bulk-download SGX legacy archives while rights remain unresolved.
3. Do not purchase JPX DataCube under the current no-paid policy.
4. JPX/OSE eligibility/right clarification remains the first cloud-side action.
5. If JPX individual access is unavailable or unsuitable, use personally licensed 225Labo locally for true-OSE HAR-RSV Stage A.
6. Raw licensed OSE data remains local/private unless explicit terms permit cloud processing or retention.

## Local device state

Remote Desktop Commander check in this round shows the authorized Windows device is still offline. No local 225Labo access, broker login, or trading action was attempted.
