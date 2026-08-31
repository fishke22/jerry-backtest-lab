# JNU source discovery — CME NKD / SGX follow-up (2026-08-31)

## Purpose
Continue free/legal source discovery before declaring true-venue intraday research blocked. This note is additive to the authoritative JNU source registry; it does not promote any proxy to true-JNU evidence.

## Newly verified public source: axb0306/cme-futures-ohlc
- Public GitHub repository: `axb0306/cme-futures-ohlc`.
- README states data are historical CME-family futures OHLCV downloaded from TopstepX / ProjectX Gateway API and updated nightly.
- Repository explicitly includes `NKD` (Nikkei 225) and timeframes tick, 1m, 5m, 15m, 30m, 1h, 4h, daily.
- Direct repository inspection on 2026-08-31 confirmed an `NKD/NKD_1min_20260308_20260415.csv` file plus 5m/tick and other resolutions. The visible NKD coverage in the repository is only about 2026-03-08 through 2026-04-15, so it is too short for robust standalone alpha validation.
- Classification: `TRUE_CME_VENUE_SHORT_SAMPLE / SUPPLEMENTARY_DPD_FEASIBILITY_ONLY`.
- It is not OSE JNU and cannot validate OSE execution or exact-product alpha.
- Raw redistribution rights are not assumed merely because the repository is public. Prefer upstream pin + hashes/provenance + derived results until source/data licensing is reviewed.

## SGX follow-up
- SGX official product material confirms yen-denominated Nikkei 225 futures and Mini Nikkei 225 futures, long trading hours, and CME mutual-offset linkage for the main yen contract.
- Barchart exposes SGX Nikkei futures and SGX Nikkei Mini daily/history pages; free site membership allows limited CSV downloads, while robust historical intraday download remains a paid/Premier path. Therefore it is not yet an approved free automated intraday history source for formal DPD.

## Research implication
The formal DPD blocker is narrowed from `OSE+SGX+CME all unavailable` to: CME has a newly verified public short intraday sample, while matched-expiry OSE and SGX historical intraday data remain unavailable under the current zero-extra-cost/approved-storage rules. Do not run a formal DPD promotion family until matched-expiry venue data and adequate coverage exist.

## Guardrails
- No proxy PASS => true-JNU PASS.
- No short-sample CME result => directional alpha.
- No scraping of sources whose terms prohibit automation.
- No paid source without explicit user authorization.
- Preserve source identity, commit/file SHA, timestamps, and transformation provenance.
