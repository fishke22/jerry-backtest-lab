# JNU Exact-Micro Realtime Entitlement Resolution — 2026-09-08

OSE real-time derivatives market data is an exchange-licensed information service. No reliable anonymous public exact individual Nikkei 225 Micro transport with positive margin inside the frozen <=900-second gate has been verified.

Current blocker: `LICENSED_REALTIME_ENTITLEMENT_REQUIRED_FOR_RELIABLE_SUB900_PATH`.

Preferred resolution order:
1. OSE one-month free trial via an approved Direct User/provider if eligible.
2. Licensed read-only real-time vendor.
3. Read-only broker feed only after an explicit later governance amendment.

The OSE free-trial process is application-based, limited to internal usage, and the published operational document is written for a company applicant that identifies the Direct User/provider supplying the information. It is not an anonymous REST/WebSocket service.

Future entitled quote evidence must satisfy `config/jnu_exact_micro_entitled_source_adapter_contract_v1.json` and pass `scripts/validate_jnu_entitled_exact_micro_evidence_v1.py`.

The validator preserves the 900-second gate and rejects stale/future timestamps, continuous contracts, broker login, trading permission, order-capable sessions, secret-like fields, unknown frozen contract months and invalid 5-point ticks. It cannot create forecasts or modify the real ledger.
