# Cloud Data Storage Policy

## Objective

Reuse data across cloud research runs without turning Git history into a raw-data warehouse or violating source licensing.

## Storage tiers

| Tier | Purpose | Current implementation | Retention |
|---|---|---|---|
| Runtime | Temporary processing | GitHub-hosted runner memory/disk | Job only |
| Cloud cache | Reusable raw downloads | GitHub Actions cache under `.cache/market-data` | Evictable; not permanent |
| Research record | Requests, parameters, source hashes, results, reports | Private Git repository | Durable |
| Durable raw-data lake | Large or long-lived raw datasets | Not enabled yet | Enable only per-source when storage/licensing is approved |

## Current behavior

- Nikkei Futures Index, FRED NASDAQ100 and FRED DEXJPUS downloads are cached in GitHub Actions.
- Raw files are not committed to Git.
- Each research result records source URLs and SHA-256 provenance.
- The Nautilus second-engine run requires the same source hashes as the first engine. A different snapshot fails closed.
- The second-engine validation on 2026-08-30 restored all three market-data inputs from cloud cache.

## Why cache is not the same as permanent storage

GitHub Actions cache is designed for reuse, not archival. It can be evicted according to repository cache retention and size policy. Therefore it is suitable for reducing repeated downloads but is not the authoritative historical data lake.

## Long-lived data rule

Before permanently archiving a raw source, classify it:

- `PUBLIC_OR_ARCHIVE_ALLOWED`: may be stored in an approved private data lake.
- `LICENSED_PRIVATE_ARCHIVE_ALLOWED`: store only under the applicable license and access controls.
- `CACHE_ONLY`: may be held temporarily for computation but not durably archived.
- `NO_STORAGE`: retrieve/process in memory and retain only derived non-reconstructive results and provenance.

Do not silently promote a CACHE_ONLY source into durable storage.

## Future data lake

When recurring datasets become large enough to justify it, add a dedicated object-storage layer rather than committing raw data to Git. The workflow registry should reference the storage adapter, while ChatGPT remains the control plane.
