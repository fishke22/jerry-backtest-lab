# JNU true-venue access resolution — round 3 (2026-08-31)

## Scope
Continue the two highest-value tasks without opening a new alpha family:
1. resolve OSE/JPX Nikkei product/security-code parsing identity;
2. resolve SGX legacy TC/WEBPXTICK product mapping using metadata-only evidence, without bulk tick acquisition.

## OSE / JPX findings

### Official one-minute schema
JPX Data Cloud public specification confirms the futures one-minute CSV schema and removes parser uncertainty. Core fields include trading/execution dates, Index_Type, 9-digit Security_Code, Session_ID, minute time, OHLC, volume, VWAP, number of trades, record number and contract month. Session_ID 999 is day session; 003 is night session.

### Nikkei 225 large and mini 9-digit identity
Official JPX historical/daily material provides direct examples:
- Nikkei 225 Futures large: codes such as `165030018` and `166030018`; product/index suffix `18` is directly evidenced.
- Nikkei 225 mini: official last-trading-day notice identifies March 2021 mini as `166030019`; product/index suffix `19` is directly evidenced.

A public tick-data example with Index_Type `18` and Security_Code `165030018` is consistent with the official large-contract identity. It is useful corroboration but primary JPX material remains authoritative.

### Nikkei 225 micro identity
Official current mappings were confirmed:
- J-Quants product category: `NK225MCF`
- QUICK: `115.n`
- Bloomberg: `JAIA <Index>`
- LSEG: `JNUcn`
- CQG: `F.US.MC225`

The Securities Identification Code Committee publication index confirms a 2023-05-25 amendment specifically associated with listing Nikkei 225 micro futures, but the currently searchable public text did not expose a production 9-digit micro issue-code example. Therefore the micro 9-digit suffix remains unresolved and MUST NOT be guessed from vendor codes.

### Remaining OSE parser blocker
None for generic one-minute parsing. Product identity can safely distinguish large (`18`) and mini (`19`). Micro parsing should use an official product-name/master mapping when available; do not hard-code a guessed suffix.

## SGX findings

### Current official product codes
SGX current product material directly identifies:
- `NK` = JPY Nikkei 225 Index Futures (outright/strategy)
- `NKTI` = Trade-At-Index-Close variant
- `NU` = USD Nikkei 225 Index Futures
- `NS` = Mini Nikkei 225 Index Futures

These are authoritative current product identifiers.

### Legacy archive structure
Independent public downloader projects continue to corroborate the historical archive family:
- `WEBPXTICK_DT`
- `TickData_structure.dat`
- `TC.txt`
- `TC_structure.dat`

One crawler reports earliest files at 2002-10-01; another uses 2004-07-23 as default historical start. Early-period filenames/formats changed, including `.tic`, `.atic1`, and `.gz` variants.

### Metadata-only retrieval attempt
A direct metadata-only attempt was considered for a single historical `TC_structure.dat` / `TC.txt` instance rather than bulk tick data. The current retrieval environment would not open the constructed SGX legacy URL because it was not surfaced as an exact safe URL from search results. No raw SGX file was downloaded and no automation was launched.

This failed retrieval attempt is an environment-routing limitation, NOT evidence that the legacy endpoint no longer exists and NOT evidence that current rights permit access.

### Legacy mapping status
Current `NK`/`NS` codes are confirmed, but no primary or safely retrievable historical `TC.txt` sample has yet proven that legacy archive records use the same product identifiers. Therefore:
`CURRENT_PRODUCT_CODES_CONFIRMED / LEGACY_TC_MAPPING_NOT_YET_PROVEN`.

## Governance implications
- No new alpha family opened.
- No proxy promoted.
- No SGX bulk acquisition under unresolved non-display/retention rights.
- No micro 9-digit suffix guessed.
- HAR-RSV Stage A remains blocked by true-OSE data access, not by parser/schema design.
- DPD remains CME-side feasible with SGX current identity partially resolved, but legacy mapping + SGX rights + OSE data access remain blockers.

## Durable companion files
- `config/jnu_source_identity_mapping_20260831.json`
- `config/jnu_research_priority_queue.json` v1.9
- `research_notes/jnu_daily_research_log_20260831.md`

## Next action
1. Search official JPX issue/reference master or daily report for a production Nikkei 225 micro 9-digit code example.
2. Search public metadata mirrors, code examples, documentation, or academic appendices for a non-raw SGX TC/TC_structure sample that exposes field definitions and historical Nikkei product codes.
3. Continue JPX individual free-trial eligibility/rights resolution; if unsuitable, use the local-only 225Labo route when the authorized Windows device becomes available.
