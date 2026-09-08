# JNU Private Entitled Live-Shadow Architecture — 2026-09-08

This stage adds a synthetic-only private forecast/outcome/scoring ledger behind the private entitled quote bridge.

The quote-free immutable request may remain public. Once entitled market data enters the chain, the forecast, outcome, hashes, decision output, and performance metrics are written only beneath a repository-external private ledger root.

No public Git commit or GitHub artifact is used for the private ledger. Stdout is intentionally redacted and does not print quote, bias, confidence, target close, return, hit, accuracy, or performance metrics.

This architecture does not authorize real entitled processing. Real OSE/provider data remains blocked until eligibility, provider transport, third-party cloud processing, and publication rights are explicitly resolved.
