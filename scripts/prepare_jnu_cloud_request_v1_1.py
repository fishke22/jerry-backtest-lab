from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jnu_integrity_hash_v1 import canonical_text_sha256
from jnu_request_preparation_validation_v1_1 import validate_prepared_request_binding

ROOT=Path(__file__).resolve().parents[1]
TAIPEI=timezone(timedelta(hours=8))
EVENT_ADAPTER=ROOT/"scripts"/"fetch_jnu_official_event_state_v1.py"
EVENT_PROTOCOL=ROOT/"config"/"jnu_official_event_state_protocol_v1_1.json"
PREP_PROTOCOL=ROOT/"config"/"jnu_cloud_request_preparation_protocol_v1_1.json"
REQUEST_PROTOCOL=ROOT/"config"/"jnu_cloud_forecast_request_protocol_v1_3.json"
DECISION=ROOT/"scripts"/"apply_jnu_operational_decision_protocol_v1.py"
DRAFT_PROTOCOL=ROOT/"config"/"jnu_cloud_request_draft_protocol_v1.json"

FORBIDDEN_DRAFT_FIELDS={
    "request_id","request_created_at_taipei","request_valid_until_taipei",
    "risk_state_evidence","request_preparation","reference_price","reference_timestamp",
    "reference_source","reference_source_metadata","bias","confidence","decision_trace",
}
REQUIRED_DRAFT_FIELDS=[
    "draft_id","analysis_frozen_at_taipei","symbol","target_day_session_date","decision_input","expected_path","key_levels",
    "invalidation_conditions","event_risk","flip_conditions","evidence_summary",
]

def load(path:Path)->dict:
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return x

def parse_dt(value:str)->datetime:
    x=datetime.fromisoformat(str(value))
    if x.tzinfo is None:
        raise RuntimeError("timestamp must be offset-aware")
    return x

def validate_draft(x:dict)->None:
    missing=[k for k in REQUIRED_DRAFT_FIELDS if k not in x]
    if missing:
        raise RuntimeError(f"missing draft fields: {missing}")
    forbidden=sorted(k for k in FORBIDDEN_DRAFT_FIELDS if k in x)
    if forbidden:
        raise RuntimeError(f"draft contains immutable/derived fields that preparer owns: {forbidden}")
    protocol=load(DRAFT_PROTOCOL)
    import re
    if not re.fullmatch(str(protocol["draft_id_pattern"]),str(x["draft_id"])):
        raise RuntimeError("invalid draft_id")
    analysis=parse_dt(str(x["analysis_frozen_at_taipei"]))
    if not isinstance(x["decision_input"],dict):
        raise RuntimeError("decision_input must be an object")
    risk=x["decision_input"].get("risk_modifiers")
    if not isinstance(risk,dict):
        raise RuntimeError("decision_input.risk_modifiers must be an object")
    supplied=risk.get("event_state")
    if supplied not in {None,"AUTO_OFFICIAL"}:
        raise RuntimeError("draft event_state must be AUTO_OFFICIAL or absent")
    if risk.get("volatility_state") not in {"NORMAL","HIGH","UNKNOWN"}:
        raise RuntimeError("draft volatility_state invalid")
    if risk.get("sq_state") not in {"NORMAL","UNRESOLVED_HIGH","UNKNOWN"}:
        raise RuntimeError("draft sq_state invalid")
    if not isinstance(risk.get("post_event_exact_jnu_path_available",False),bool):
        raise RuntimeError("post_event_exact_jnu_path_available must be boolean")
    if not isinstance(x["key_levels"],list) or not x["key_levels"]:
        raise RuntimeError("key_levels must be a non-empty array")
    for k in ["expected_path","invalidation_conditions","event_risk","flip_conditions","evidence_summary"]:
        if not str(x[k]).strip():
            raise RuntimeError(f"{k} must be non-empty")

def run_event_adapter(target:str)->dict:
    with tempfile.TemporaryDirectory(prefix="jnu_event_prepare_") as td:
        out=Path(td)/"event.json"
        cp=subprocess.run(
            [sys.executable,str(EVENT_ADAPTER),"--target-day-session-date",target,"--output",str(out)],
            cwd=ROOT,capture_output=True,text=True,check=False,
        )
        if not out.exists():
            raise RuntimeError(f"official event-state adapter produced no output: {(cp.stderr or cp.stdout).strip()}")
        x=load(out)
        if cp.returncode not in {0,3}:
            raise RuntimeError(f"official event-state adapter failed: {(cp.stderr or cp.stdout).strip()}")
        return x

def run_decision(decision_input:dict)->dict:
    with tempfile.TemporaryDirectory(prefix="jnu_prepare_decision_") as td:
        inp=Path(td)/"input.json"; out=Path(td)/"trace.json"
        inp.write_text(json.dumps(decision_input,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        cp=subprocess.run(
            [sys.executable,str(DECISION),"--input",str(inp),"--output",str(out)],
            cwd=ROOT,capture_output=True,text=True,check=False,
        )
        if cp.returncode!=0:
            raise RuntimeError(f"decision protocol rejected prepared input: {(cp.stderr or cp.stdout).strip()}")
        return load(out)

def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--draft",type=Path,required=True)
    ap.add_argument("--output",type=Path)
    ap.add_argument("--selftest",action="store_true")
    ap.add_argument("--event-evidence-file",type=Path)
    ap.add_argument("--request-created-at-taipei")
    args=ap.parse_args()

    draft=load(args.draft)
    validate_draft(draft)

    if (args.event_evidence_file or args.request_created_at_taipei) and not args.selftest:
        raise RuntimeError("synthetic event evidence/time overrides are selftest-only")

    event_result=load(args.event_evidence_file) if args.event_evidence_file else run_event_adapter(str(draft["target_day_session_date"]))
    if str(event_result.get("target_day_session_date"))!=str(draft["target_day_session_date"]):
        raise RuntimeError("event-state target date mismatch")
    if event_result.get("protocol")!="config/jnu_official_event_state_protocol_v1_1.json":
        raise RuntimeError("event-state producer protocol mismatch")
    state=str(event_result.get("event_state"))
    if state=="UNKNOWN":
        raise RuntimeError("official event_state UNKNOWN: immutable request creation blocked")
    if state not in {"NORMAL","PRE_RELEASE_HIGH","POST_EVENT_HIGH"}:
        raise RuntimeError("official event_state invalid")
    failures=event_result.get("source_failures")
    if failures not in ([],None):
        raise RuntimeError(f"official event-state required-source failures remain: {failures}")

    evidence=dict(event_result.get("risk_state_evidence") or {})
    sources=evidence.get("event_sources")
    required_count=len(load(EVENT_PROTOCOL)["required_sources"])
    if not isinstance(sources,list) or len(sources)!=required_count:
        raise RuntimeError(f"official event source coverage incomplete: expected {required_count}, got {len(sources) if isinstance(sources,list) else 0}")

    decision_input=json.loads(json.dumps(draft["decision_input"]))
    risk=decision_input["risk_modifiers"]
    risk["event_state"]=state
    evidence["event_state"]=state
    evidence["volatility_state"]=risk["volatility_state"]
    evidence["sq_state"]=risk["sq_state"]
    evidence["event_state_protocol"]="config/jnu_official_event_state_protocol_v1_1.json"
    evidence["event_state_protocol_sha256"]=canonical_text_sha256(EVENT_PROTOCOL)
    evidence["event_state_producer"]="scripts/fetch_jnu_official_event_state_v1.py"
    evidence["request_preparation_protocol"]="config/jnu_cloud_request_preparation_protocol_v1_1.json"
    evidence["request_preparation_protocol_sha256"]=canonical_text_sha256(PREP_PROTOCOL)
    evidence["required_event_source_coverage"]=required_count
    evidence["observed_event_source_coverage"]=len(sources)
    evidence["event_source_failures"]=failures or []

    trace=run_decision(decision_input)
    if (trace.get("risk_modifiers") or {}).get("event_state")!=state:
        raise RuntimeError("decision trace did not preserve official event state")

    created=parse_dt(args.request_created_at_taipei).astimezone(TAIPEI) if args.request_created_at_taipei else datetime.now(TAIPEI)
    analysis=parse_dt(str(draft["analysis_frozen_at_taipei"])).astimezone(TAIPEI)
    analysis_age=(created-analysis).total_seconds()
    if analysis_age<0 or analysis_age>900:
        raise RuntimeError(f"analysis draft freshness exceeds 900 seconds at request creation: age={analysis_age:.1f}s")
    checked=parse_dt(evidence["checked_at_taipei"]).astimezone(TAIPEI)
    if checked>created:
        raise RuntimeError("official event evidence occurs after request creation")
    age=(created-checked).total_seconds()
    if age<0 or age>900:
        raise RuntimeError(f"official event evidence too old at request creation: {age:.1f}s")
    for src in sources:
        schecked=parse_dt(src["checked_at_taipei"]).astimezone(TAIPEI)
        sage=(created-schecked).total_seconds()
        if sage<0 or sage>900:
            raise RuntimeError(f"official event source evidence stale at request creation: {src.get('source')} age={sage:.1f}s")

    valid_until=created+timedelta(seconds=900)
    draft_fingerprint=hashlib.sha256(
        json.dumps(draft,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
    ).hexdigest()[:12]
    rid=f"JNU_REQ_{created.strftime('%Y%m%dT%H%M%S')}_{draft_fingerprint}"

    req={
        "request_id":rid,
        "draft_id":str(draft["draft_id"]),
        "request_created_at_taipei":created.isoformat(),
        "analysis_frozen_at_taipei":analysis.isoformat(),
        "request_valid_until_taipei":valid_until.isoformat(),
        "symbol":str(draft["symbol"]).upper(),
        "target_day_session_date":str(draft["target_day_session_date"]),
        "decision_input":decision_input,
        "risk_state_evidence":evidence,
        "expected_path":draft["expected_path"],
        "key_levels":draft["key_levels"],
        "invalidation_conditions":draft["invalidation_conditions"],
        "event_risk":draft["event_risk"],
        "flip_conditions":draft["flip_conditions"],
        "evidence_summary":draft["evidence_summary"],
        "request_preparation":{
            "protocol":"config/jnu_cloud_request_preparation_protocol_v1_1.json",
            "protocol_sha256":canonical_text_sha256(PREP_PROTOCOL),
            "request_protocol":"config/jnu_cloud_forecast_request_protocol_v1_3.json",
            "request_protocol_sha256":canonical_text_sha256(REQUEST_PROTOCOL),
            "official_event_state":state,
            "decision_protocol_sha256":trace["protocol_sha256"],
            "draft_protocol":"config/jnu_cloud_request_draft_protocol_v1.json",
            "draft_protocol_sha256":canonical_text_sha256(DRAFT_PROTOCOL),
            "draft_id":str(draft["draft_id"]),
            "analysis_frozen_at_taipei":analysis.isoformat(),
            "analysis_age_at_request_seconds":analysis_age,
            "real_registration_performed":False,
        },
    }
    validate_prepared_request_binding(req, decision_event_state=state)

    output=args.output or (ROOT/"live_shadow_requests"/f"{rid}.json")
    if output.exists():
        raise RuntimeError(f"request output already exists: {output}")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(req,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":"IMMUTABLE_JNU_CLOUD_REQUEST_PREPARED_V1_1",
        "request_id":rid,
        "draft_id":str(draft["draft_id"]),
        "analysis_age_at_request_seconds":analysis_age,
        "event_state":state,
        "event_source_coverage":len(sources),
        "evidence_age_at_request_seconds":age,
        "request_valid_until_taipei":valid_until.isoformat(),
        "decision_bias":trace["bias"],
        "decision_confidence":trace["confidence"],
        "output":str(output),
        "real_registration_performed":False,
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
