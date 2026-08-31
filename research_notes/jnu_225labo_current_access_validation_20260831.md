# 225Labo current-access validation — 2026-08-31

## Verified public-source facts

225Labo's current Nikkei 225 mini page states:

- minute data are available from 2006 onward;
- supported minute intervals are 1, 3, 5, 10, 15, 20, 30 and 60 minutes;
- registered members may download the data free of charge;
- use is licensed only to the person who downloaded the data;
- provision/sale or similar transfer to third parties is prohibited.

225Labo's current Nikkei 225 micro page states:

- minute data are available from 2023-07-24 onward;
- daily data are available from 2023-05-29 onward;
- supported minute intervals are 1, 3, 5, 10, 15, 20, 30 and 60 minutes;
- registered members may download the data free of charge;
- the same downloader-only / no-third-party-transfer restriction applies.

The general 225Labo download terms state that the data are made available for the individual user's learning/improvement of trading ability, at the user's own risk, and prohibit use outside the stated purpose including commercial use.

## Research interpretation

This materially strengthens the existing local-only source decision:

`225LABO_OSE_NIKKEI_MINUTE = BEST_CURRENT_NO_EXTRA_COST_TRUE_OSE_FALLBACK`

It is a true OSE-market-history path suitable for the frozen source hierarchy, but not a cloud raw-data source.

### Frozen validation sequence

1. **Stage A — Nikkei 225 mini long-history confirmation**
   - Use the 5-minute series derived from the 225Labo minute data.
   - Preserve the already frozen HAR-RSV methodology and gates.
   - Do not tune parameters after seeing Stage A outcomes.

2. **Stage B — Nikkei 225 micro exact-product consistency**
   - Use JNU micro data from 2023-07-24 onward if Stage A passes.
   - No parameter retuning between Stage A and Stage B.
   - A short micro sample cannot rescue a failed Stage A.

3. **Later true-OSE intraday directional test**
   - Only after volatility/risk-stage work and only under the already frozen `INTRADAY_PATH_US_TO_JNU_G1` specification.
   - No further proxy-rescue variants.

## Storage / processing boundary

- Raw downloaded 225Labo files remain on the user's local Windows machine.
- Do not upload raw files, credentials, session cookies, or reconstructable raw bars to GitHub, Vercel, ChatGPT storage, or other cloud services.
- Local processing may produce non-reconstructable derived RV/RSV features, hashes, provenance manifests, diagnostics, and aggregate research results for durable private-GitHub storage.
- Exact file schema must be inspected locally before implementation; do not guess headers or timestamp fields from public pages.

## Current execution blocker

Remote Desktop Commander check on 2026-08-31 found the authorized Windows device present but **offline**. Therefore no local 225Labo download/schema inspection was attempted in this research turn.

While the device remains offline, continue cloud-side governance, source-rights work, and acquisition planning only. When the device comes online, the immediate next local step is exact schema/sample inspection followed by Gate 0 data-integrity checks for HAR-RSV Stage A.
