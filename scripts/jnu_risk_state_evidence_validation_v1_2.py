from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
from jnu_integrity_hash_v1 import canonical_text_sha256

EVENT_STATES={"NORMAL","PRE_RELEASE_HIGH","POST_EVENT_HIGH","UNKNOWN"}
VOL_STATES={"NORMAL","HIGH","UNKNOWN"}
SQ_STATES={"NORMAL","UNRESOLVED_HIGH","UNKNOWN"}
ROOT=Path(__file__).resolve().parents[1]
EVENT_PROTOCOL=ROOT/"config"/"jnu_official_event_state_protocol_v1_1.json"
PREP_PROTOCOL=ROOT/"config"/"jnu_cloud_request_preparation_protocol_v1_1.json"

def parse_dt(s:str)->datetime:
    x=datetime.fromisoformat(str(s))
    if x.tzinfo is None:
        raise RuntimeError("risk evidence timestamp must be offset-aware")
    return x

def validate_risk_state_evidence(
    evidence:dict,
    decision_trace:dict,
    forecast_created_at:str,
    request_created_at:str|None=None,
    target_day_session_date:str|None=None,
)->dict:
    if not isinstance(evidence,dict):
        raise RuntimeError("risk_state_evidence missing")
    checked=parse_dt(evidence.get("checked_at_taipei"))
    created=parse_dt(forecast_created_at)
    request_anchor=parse_dt(request_created_at) if request_created_at else created
    age_at_request=(request_anchor-checked).total_seconds()
    age_at_forecast=(created-checked).total_seconds()
    if age_at_request<0 or age_at_request>900:
        raise RuntimeError("risk_state_evidence must be frozen no more than 900 seconds before request creation")
    if age_at_forecast<0 or age_at_forecast>900:
        raise RuntimeError("risk_state_evidence is older than 900 seconds at forecast creation")

    risk=(decision_trace or {}).get("risk_modifiers") or {}
    for key,allowed in [
        ("event_state",EVENT_STATES),
        ("volatility_state",VOL_STATES),
        ("sq_state",SQ_STATES),
    ]:
        value=evidence.get(key)
        if value not in allowed:
            raise RuntimeError(f"invalid risk evidence {key}")
        if value!=risk.get(key):
            raise RuntimeError(f"risk evidence mismatch: {key}")
    if target_day_session_date is not None:
        if str(evidence.get("target_day_session_date"))!=str(target_day_session_date):
            raise RuntimeError("risk evidence target day mismatch")

    event_state=evidence.get("event_state")
    sources=evidence.get("event_sources")
    if event_state=="UNKNOWN":
        if not str(evidence.get("event_unavailability_reason","")).strip():
            raise RuntimeError("event UNKNOWN requires event_unavailability_reason")
    else:
        if evidence.get("event_state_protocol")!="config/jnu_official_event_state_protocol_v1_1.json":
            raise RuntimeError("risk evidence event-state protocol path mismatch")
        if evidence.get("event_state_protocol_sha256")!=canonical_text_sha256(EVENT_PROTOCOL):
            raise RuntimeError("risk evidence event-state protocol SHA mismatch")
        if evidence.get("event_state_producer")!="scripts/fetch_jnu_official_event_state_v1.py":
            raise RuntimeError("risk evidence event-state producer mismatch")
        if evidence.get("request_preparation_protocol")!="config/jnu_cloud_request_preparation_protocol_v1_1.json":
            raise RuntimeError("risk evidence preparation protocol path mismatch")
        if evidence.get("request_preparation_protocol_sha256")!=canonical_text_sha256(PREP_PROTOCOL):
            raise RuntimeError("risk evidence preparation protocol SHA mismatch")

        required=set(json.loads(EVENT_PROTOCOL.read_text(encoding="utf-8"))["required_sources"])
        if not isinstance(sources,list) or len(sources)!=len(required):
            raise RuntimeError("known event state requires complete official event source coverage")
        source_ids=[]
        for src in sources:
            if not isinstance(src,dict):
                raise RuntimeError("event source must be an object")
            if not str(src.get("source","")).strip() or not str(src.get("reference","")).strip():
                raise RuntimeError("event source identity/reference missing")
            source_ids.append(str(src.get("source")))
            if int(src.get("http_status",-1))!=200:
                raise RuntimeError("event source HTTP status must be 200")
            if int(src.get("parsed_event_count",0))<=0:
                raise RuntimeError("event source parsed_event_count must be positive")
            schecked=parse_dt(src.get("checked_at_taipei"))
            if schecked>request_anchor:
                raise RuntimeError("event source check occurs after request creation")
            if (request_anchor-schecked).total_seconds()>900:
                raise RuntimeError("event source check is older than 900 seconds at request creation")
            if (created-schecked).total_seconds()>900:
                raise RuntimeError("event source check is older than 900 seconds at forecast creation")
        if set(source_ids)!=required or len(source_ids)!=len(required):
            raise RuntimeError("official event source IDs do not match frozen required coverage")
        if int(evidence.get("required_event_source_coverage",-1))!=len(required):
            raise RuntimeError("required event source coverage count mismatch")
        if int(evidence.get("observed_event_source_coverage",-1))!=len(required):
            raise RuntimeError("observed event source coverage count mismatch")
        if evidence.get("event_source_failures") not in ([],None):
            raise RuntimeError("known event state retains official event source failures")

    return {
        "checked_at_taipei":checked.isoformat(),
        "age_at_request_seconds":age_at_request,
        "age_at_forecast_seconds":age_at_forecast,
        "event_state":event_state,
        "volatility_state":evidence.get("volatility_state"),
        "sq_state":evidence.get("sq_state"),
        "event_source_count":len(sources) if isinstance(sources,list) else 0,
        "official_event_provenance_verified":event_state!="UNKNOWN",
        "target_day_session_date":str(evidence.get("target_day_session_date","")),
    }
