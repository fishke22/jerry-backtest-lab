# JNU Private Entitled Quote Bridge Scaffold — 2026-09-08

This stage adds a private-only raw quote bridge scaffold. It is synthetic-tested in CI and is not a real OSE Free Trial integration.

Hard boundaries:
- evidence input must resolve outside the public repository;
- permission manifest must resolve outside the public repository;
- private store root/output must resolve outside the public repository;
- public output requests are rejected;
- unapproved third-party cloud processing is rejected;
- stdout never prints raw price or provider timestamp;
- no decision engine, forecast, public hash, public derived result, or real ledger mutation.

Real entitled data must not be processed in GitHub Actions until explicit OSE/provider cloud permission exists.
