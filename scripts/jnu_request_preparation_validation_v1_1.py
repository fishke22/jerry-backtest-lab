from __future__ import annotations

from pathlib import Path
import re
from datetime import datetime

from jnu_integrity_hash_v1 import canonical_text_sha256

ROOT=Path(__file__).resolve().parents[1]
PREP_PROTOCOL=ROOT/"config"/"jnu_cloud_request_preparation_protocol_v1_1.json"
REQUEST_PROTOCOL=ROOT/"config"/"jnu_cloud_forecast_request_protocol_v1_3.json"
EVENT_PROTOCOL=ROOT/"config"/"jnu_official_event_state_protocol_v1_1.json"
DECISION_PROTOCOL=ROOT/"config"/"jnu_operational_decision_protocol_v1.json"
DRAFT_PROTOCOL=ROOT/"config"/"jnu_cloud_request_draft_protocol_v1.json"

EXPECTED_PREP_PATH="config/jnu_cloud_request_preparation_protocol_v1_1.json"
EXPECTED_REQUEST_PATH="config/jnu_cloud_forecast_request_protocol_v1_3.json"
EXPECTED_EVENT_PATH="config/jnu_official_event_state_protocol_v1_1.json"
EXPECTED_EVENT_PRODUCER="scripts/fetch_jnu_official_event_state_v1.py"
EXPECTED_DRAFT_PATH="config/jnu_cloud_request_draft_protocol_v1.json"

def validate_prepared_request_binding(x:dict, decision_event_state:str|None=None)->dict:
    if not isinstance(x,dict):
        raise RuntimeError("prepared request/forecast must be an object")
    rp=x.get("request_preparation")
    if not isinstance(rp,dict):
        raise RuntimeError("request_preparation missing")
    if rp.get("protocol")!=EXPECTED_PREP_PATH:
        raise RuntimeError("request_preparation protocol path mismatch")
    if rp.get("protocol_sha256")!=canonical_text_sha256(PREP_PROTOCOL):
        raise RuntimeError("request_preparation protocol SHA mismatch")
    if rp.get("request_protocol")!=EXPECTED_REQUEST_PATH:
        raise RuntimeError("request_preparation request protocol path mismatch")
    if rp.get("request_protocol_sha256")!=canonical_text_sha256(REQUEST_PROTOCOL):
        raise RuntimeError("request_preparation request protocol SHA mismatch")
    if rp.get("decision_protocol_sha256")!=canonical_text_sha256(DECISION_PROTOCOL):
        raise RuntimeError("request_preparation decision protocol SHA mismatch")
    if rp.get("real_registration_performed") is not False:
        raise RuntimeError("request_preparation real_registration_performed must be false")
    if rp.get("draft_protocol")!=EXPECTED_DRAFT_PATH:
        raise RuntimeError("request_preparation draft protocol path mismatch")
    if rp.get("draft_protocol_sha256")!=canonical_text_sha256(DRAFT_PROTOCOL):
        raise RuntimeError("request_preparation draft protocol SHA mismatch")

    draft_id=str(x.get("draft_id",""))
    pattern=__import__("json").loads(DRAFT_PROTOCOL.read_text(encoding="utf-8"))["draft_id_pattern"]
    if not re.fullmatch(pattern,draft_id):
        raise RuntimeError("prepared request draft_id invalid")
    if rp.get("draft_id")!=draft_id:
        raise RuntimeError("request_preparation draft_id mismatch")

    analysis_raw=str(x.get("analysis_frozen_at_taipei",""))
    request_raw=str(x.get("request_created_at_taipei",""))
    try:
        analysis_dt=datetime.fromisoformat(analysis_raw)
        request_dt=datetime.fromisoformat(request_raw)
    except Exception as exc:
        raise RuntimeError(f"prepared request analysis/request timestamp invalid: {exc}")
    if analysis_dt.tzinfo is None or request_dt.tzinfo is None:
        raise RuntimeError("prepared request analysis/request timestamps must be offset-aware")
    analysis_age=(request_dt-analysis_dt).total_seconds()
    if analysis_age<0 or analysis_age>900:
        raise RuntimeError("prepared request analysis draft freshness exceeds 900 seconds")
    if rp.get("analysis_frozen_at_taipei")!=analysis_raw:
        raise RuntimeError("request_preparation analysis freeze timestamp mismatch")
    try:
        stored_age=float(rp.get("analysis_age_at_request_seconds"))
    except Exception:
        raise RuntimeError("request_preparation analysis age missing")
    if abs(stored_age-analysis_age)>1e-9:
        raise RuntimeError("request_preparation analysis age mismatch")

    evidence=x.get("risk_state_evidence")
    if not isinstance(evidence,dict):
        raise RuntimeError("risk_state_evidence missing")
    if evidence.get("event_state_protocol")!=EXPECTED_EVENT_PATH:
        raise RuntimeError("risk evidence event-state protocol path mismatch")
    if evidence.get("event_state_protocol_sha256")!=canonical_text_sha256(EVENT_PROTOCOL):
        raise RuntimeError("risk evidence event-state protocol SHA mismatch")
    if evidence.get("event_state_producer")!=EXPECTED_EVENT_PRODUCER:
        raise RuntimeError("risk evidence event-state producer mismatch")
    if evidence.get("request_preparation_protocol")!=EXPECTED_PREP_PATH:
        raise RuntimeError("risk evidence preparation protocol path mismatch")
    if evidence.get("request_preparation_protocol_sha256")!=canonical_text_sha256(PREP_PROTOCOL):
        raise RuntimeError("risk evidence preparation protocol SHA mismatch")

    event_state=evidence.get("event_state")
    if event_state not in {"NORMAL","PRE_RELEASE_HIGH","POST_EVENT_HIGH"}:
        raise RuntimeError("prepared request requires known official event state")
    if rp.get("official_event_state")!=event_state:
        raise RuntimeError("request_preparation official event state mismatch")
    if decision_event_state is None:
        di=x.get("decision_input")
        if isinstance(di,dict):
            decision_event_state=(di.get("risk_modifiers") or {}).get("event_state")
        else:
            tr=x.get("decision_trace")
            if isinstance(tr,dict):
                decision_event_state=(tr.get("risk_modifiers") or {}).get("event_state")
    if decision_event_state!=event_state:
        raise RuntimeError("prepared request decision event state mismatch")

    protocol=__import__("json").loads(EVENT_PROTOCOL.read_text(encoding="utf-8"))
    required=set(protocol["required_sources"])
    sources=evidence.get("event_sources")
    if not isinstance(sources,list):
        raise RuntimeError("prepared request event sources missing")
    source_ids=[str(s.get("source","")) for s in sources if isinstance(s,dict)]
    if set(source_ids)!=required or len(source_ids)!=len(required):
        raise RuntimeError("prepared request official event source coverage mismatch")
    if int(evidence.get("required_event_source_coverage",-1))!=len(required):
        raise RuntimeError("prepared request required event source count mismatch")
    if int(evidence.get("observed_event_source_coverage",-1))!=len(required):
        raise RuntimeError("prepared request observed event source count mismatch")
    failures=evidence.get("event_source_failures")
    if failures not in ([],None):
        raise RuntimeError("prepared request retains official event source failures")

    for src in sources:
        if not isinstance(src,dict):
            raise RuntimeError("prepared request event source must be an object")
        if int(src.get("http_status",-1))!=200:
            raise RuntimeError(f"prepared request event source HTTP status invalid: {src.get('source')}")
        if int(src.get("parsed_event_count",0))<=0:
            raise RuntimeError(f"prepared request event source parsed_event_count invalid: {src.get('source')}")
        if not str(src.get("reference","")).strip():
            raise RuntimeError(f"prepared request event source reference missing: {src.get('source')}")

    return {
        "status":"PASS",
        "official_event_state":event_state,
        "official_event_source_coverage":len(required),
        "draft_id":draft_id,
        "analysis_frozen_at_taipei":analysis_raw,
        "analysis_age_at_request_seconds":analysis_age,
        "analysis_draft_protocol_sha256":canonical_text_sha256(DRAFT_PROTOCOL),
        "request_preparation_protocol_sha256":canonical_text_sha256(PREP_PROTOCOL),
        "request_protocol_sha256":canonical_text_sha256(REQUEST_PROTOCOL),
        "event_state_protocol_sha256":canonical_text_sha256(EVENT_PROTOCOL),
        "decision_protocol_sha256":canonical_text_sha256(DECISION_PROTOCOL),
    }
