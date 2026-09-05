from __future__ import annotations
from datetime import datetime

EVENT_STATES={"NORMAL","PRE_RELEASE_HIGH","POST_EVENT_HIGH","UNKNOWN"}
VOL_STATES={"NORMAL","HIGH","UNKNOWN"}
SQ_STATES={"NORMAL","UNRESOLVED_HIGH","UNKNOWN"}

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
        if not isinstance(sources,list) or not sources:
            raise RuntimeError("known event state requires at least one event source")
        for src in sources:
            if not isinstance(src,dict):
                raise RuntimeError("event source must be an object")
            if not str(src.get("source","")).strip() or not str(src.get("reference","")).strip():
                raise RuntimeError("event source identity/reference missing")
            schecked=parse_dt(src.get("checked_at_taipei"))
            if schecked>request_anchor:
                raise RuntimeError("event source check occurs after request creation")
            if (request_anchor-schecked).total_seconds()>900:
                raise RuntimeError("event source check is older than 900 seconds at request creation")
            if (created-schecked).total_seconds()>900:
                raise RuntimeError("event source check is older than 900 seconds at forecast creation")

    return {
        "checked_at_taipei":checked.isoformat(),
        "age_at_request_seconds":age_at_request,
        "age_at_forecast_seconds":age_at_forecast,
        "event_state":event_state,
        "volatility_state":evidence.get("volatility_state"),
        "sq_state":evidence.get("sq_state"),
        "event_source_count":len(sources) if isinstance(sources,list) else 0,
        "target_day_session_date":str(evidence.get("target_day_session_date","")),
    }
