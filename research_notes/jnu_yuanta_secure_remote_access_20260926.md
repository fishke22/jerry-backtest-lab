# JNU Yuanta Secure Remote Access

## Conclusion

The login code may be stored in GitHub. Broker credentials must not be stored in repository files.

A password hash cannot be used for Yuanta login because the API requires the original account/password at runtime. Hashing is one-way authentication verification, not reversible secret storage.

## What GitHub should contain

- Yuanta quote-only login/runtime code
- exact JNU contract-resolution logic
- deployment configuration
- health checks and CI
- names of required secrets, never their values

## What GitHub should not contain

- account number
- password
- PFX/certificate private key
- certificate password
- reversible encrypted secret plus its decryption key
- password hash represented as if it can be passed to Yuanta Login()

## Current local implementation

The existing source of truth remains `D:\MARKET_AI_HUB`:

- `src/market_ai_hub/integrations/yuanta/spark_runtime.py`
- `src/market_ai_hub/integrations/yuanta/credential_store.py`
- `src/market_ai_hub/integrations/yuanta/live_quote_recorder.py`

Its tested login semantics are:

```text
load YuantaSparkAPI
Open(PROD)
wait official CONNECT event
Login(account, password)
wait OnResponse(strIndex="Login")
require MsgCode 0001/00001
subscribe quote-only JNU data
never expose order APIs
```

Credentials currently belong in Windows Credential Manager, not the repository.

## Why GitHub Actions alone does not solve mobile realtime data

GitHub-hosted Actions VMs are created for jobs and destroyed after jobs. They are suitable for bounded jobs, CI, deployment and one-shot probes, but they are not an always-on live market-data server.

A self-hosted runner can run on the user's home PC, but then the home PC still has to remain online. That does not solve the user's requirement when the home machine is unavailable.

## Preferred remote design

To make mobile access independent of the home PC:

```text
GitHub
  -> deploy code
Persistent Windows cloud VM
  -> Yuanta SPARK quote-only runtime
  -> account/password from Windows Credential Manager or cloud secret vault
  -> exact JNU quote/tick/depth (only what entitlement actually returns)
  -> private authenticated read-only HTTPS/MCP endpoint
ChatGPT mobile
  -> private plugin/MCP
  -> latest JNU data
```

GitHub can optionally hold workflow secrets for deployment or bounded probes. The persistent broker credential should preferably remain in the runtime host's secret store / cloud vault, not in repository content.

## Current status

`DESIGN_READY_NOT_REMOTE_ACTIVATED`

The architecture is technically plausible, but real Yuanta login from a cloud Windows VM has not yet been proven. Until that validation passes, JNU Research must continue using the existing fallback ladder:

1. local exact Yuanta when available;
2. user mobile exact quote/screenshot anchor;
3. cloud/plugin/official proxy context;
4. abstain if critical data cannot be refreshed safely.

No claim of remote exact Yuanta availability is allowed before an actual VM login + exact JNU quote callback is observed.
