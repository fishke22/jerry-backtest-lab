# JNU QROS local-source inventory — 2026-08-31

## Scope and safety
Read-only inspection of `D:\QROS` on the authorized local Windows device. No broker login was initiated, no account-query payloads were read for research use, no order/trading action was attempted, and no credentials were copied. Existing Yuanta manifests were inspected only for static product identity and whether historical JNU market captures already existed.

## Major discovery: true-OSE daily/session data already exists locally
The prior cloud-only assumption that true-OSE data were broadly unavailable was too coarse. QROS already contains a substantial official JPX/NDL OSE research corpus.

### Exact OSE Micro daily/session data
- Canonical local source chain: JPX public Daily Report PDFs -> `jpx_daily_all_rows_v1_0_3.json` -> `build_continuous_jnu.py` -> `jnu_continuous_micro_v1.parquet/csv`.
- Continuous exact-product Micro series: 364 distinct trading days, 2025-02-03 through 2026-07-30.
- 19 actual Micro contracts and 18 rolls in the existing continuous build.
- Common day-session normalized corpus contains 1,455 Micro contract rows across the same 364 days.
- Example 2025-02-03 official JPX row: `trading_code=160030023`, product MICRO, multiplier 10, tick size 5, source `JPX_PUBLIC_DAILY_REPORT`.
- This independently cross-checks the official JPX Micro target-index suffix/classification `23`.

### Exact OSE Mini long-history day-session data
- `nikkei_common_day_session_v1.json` contains 14,999 Mini contract rows.
- 1,250 distinct Mini trading days, 2015-12-01 through 2026-07-30.
- Early segment uses `NDL_ARCHIVED_OSE_DAILY_REPORT`; later segment uses JPX public Daily Reports.
- The dataset is explicitly `COMMON_DAY_SESSION`; overnight/intraday-sequence features are marked unavailable.

### Existing NDL archive work
- QROS already has `NDL_OSE_ITEM_INDEX_v2.csv`: 1,414 metadata items covering 2014-03-24 through 2019-12-30.
- Existing 2026-08-09 reports already investigated JPX Monthly/Annual/Daily and NDL/WARP access/rights.
- NDL metadata discovery is allowed only under the documented fail-closed, low-frequency rules; content rights are separate.
- Future JNU sessions must not redo this archive discovery from scratch.

## Existing local raw/derived corpus
- Hundreds of JPX Daily Report PDFs under `D:\QROS\data\ose_free\raw\jpx\daily_reports`.
- JPX Monthly Quotations `SIF_M` files from 2023-05 through 2026-06.
- JPX Monthly Statistics `SIF_D` files from 2023-05 through 2026-06.
- Annual Quotations 2016-2025.
- NDL metadata, landing evidence, samples, daily archives and parser receipts.
- Normalized per-date JPX rows, NDL parsed rows, common day-session rows, and continuous Micro daily series.
- Source hashes, parser versions, DQ reports, download receipts and provenance are already present.

## What this DOES unblock
- Exact-product OSE Micro daily identity/contract/roll sanity checks.
- Exact OSE Mini long-history daily/session regime studies that are preregistered for daily/session grain.
- Cross-era data-quality checks and contract-spec/roll validation.
- Daily/session exact-product confirmation for modules whose preregistration explicitly allows that grain.
- Reuse of QROS ingestion, parser, DQ and provenance engineering instead of rewriting them.

## What this DOES NOT unblock
- HAR-RSV Stage A, because the frozen primary measurement is 5-minute RV/RSV. Daily/session OHLC cannot be expanded into 5-minute realized variance or semivariance.
- FIRST30/LAST30 intraday path tests.
- True-venue DPD lead-lag/price-discovery tests.
- Order imbalance or limit-order-book research.
- Exact intraday execution/VWAP-reclaim path modules.

## Existing real-time/Yuanta captures
- The existing 2026-07 realtime-research manifests/snapshots contain test/TWSE research artifacts; content search found no JNU historical capture.
- Static Yuanta FunctionList evidence maps Micro root `JNU` and quote codes such as `JNU2606`, `JNU2609`, `JNUPM2606`, `JNUPM2609`.
- Existing LIVE0 receipt found no JNU watchlist item at that prior run.
- No new broker connection or quote request was made in this inventory.

## Revised blocker
The correct blocker is no longer "true OSE history unavailable." It is:
`TRUE_OSE_INTRADAY_1M_5M_HISTORY_NOT_YET_LOCATED_OR_ACQUIRED`.

The preferred next route is local 225Labo Mini minute history (raw local-only under its personal-use terms), with JPX official historical trial/DataCube eligibility as an alternate acquisition path. Do not reconstruct intraday bars from session OHLC and do not promote legacy QROS exploratory strategy PnL into the current JNU validation lineage.
