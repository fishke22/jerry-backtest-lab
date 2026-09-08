# JNU Production Key Custody / Provider-Term Gate Seal — 2026-09-08

Core commit: `a123a902b72bfcca4d56cf572c495d4ecefbea9e`

Cloud verification:
- Integrity `34206608446`: PASS.
- Actionlint `34206608455`: PASS.
- Production key-custody/provider-term selftest: **30/30 PASS**.
- Existing encrypted backup selftest: 30/30 PASS.
- Public real ledger remains 0 forecasts / 0 outcomes.
- Stable v1.9 framework SHA: `57b94457bff146271e8c48e410bd5e16178c0050fc271c808d67abf4af418928`.

Production control-class decision:
- preferred: MANAGED_HSM_BACKED_KMS;
- escalation: DEDICATED_HSM_OR_CUSTOM_KEY_STORE only if OSE/provider contract or internal policy requires subscriber-controlled/dedicated HSM;
- prohibited: synthetic file keyring, plaintext/exportable software KEK, environment-variable KEK, GitHub Actions secret KEK, shared human credential.

The synthetic fully-approved profiles can reach READY. The current repository manifests intentionally remain BLOCKED because vendor/region/key are unselected and real OSE/provider evidence is unresolved.

Real encrypted backup/restore remains prohibited. No real KMS credential, real entitlement data, or public derived output was introduced.
