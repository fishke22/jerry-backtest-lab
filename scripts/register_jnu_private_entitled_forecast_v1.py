from __future__ import annotations
import argparse,hashlib,json,subprocess,sys
from datetime import datetime,timezone,timedelta
from pathlib import Path
from build_jnu_cloud_forecast_input_v1_2 import validate_request
from jnu_request_preparation_validation_v1_1 import validate_prepared_request_binding
from jnu_risk_state_evidence_validation_v1_2 import validate_risk_state_evidence
from jnu_integrity_hash_v1 import canonical_text_sha256
from jnu_private_atomic_io_v1 import require_external,verify_backup,write_immutable_json
from validate_jnu_entitled_exact_micro_evidence_v1 import validate as validate_entitled_quote
ROOT=Path(__file__).resolve().parents[1];TAIPEI=timezone(timedelta(hours=8));DECISION=ROOT/"scripts"/"apply_jnu_operational_decision_protocol_v1.py"
FRAMEWORK=ROOT/"config"/"jnu_operational_framework_current_v1_9.json";PREREG=ROOT/"config"/"jnu_operational_live_shadow_prereg_v1_7.json";IMPL=ROOT/"config"/"jnu_operational_live_shadow_implementation_v1_7.json";PROTOCOL=ROOT/"config"/"jnu_operational_decision_protocol_v1.json";HASH_PROTOCOL=ROOT/"config"/"jnu_integrity_hash_protocol_v1.json";REQUEST_PROTOCOL=ROOT/"config"/"jnu_cloud_forecast_request_protocol_v1_3.json";PREP_PROTOCOL=ROOT/"config"/"jnu_cloud_request_preparation_protocol_v1_1.json";EVENT_PROTOCOL=ROOT/"config"/"jnu_official_event_state_protocol_v1_1.json";DRAFT_PROTOCOL=ROOT/"config"/"jnu_cloud_request_draft_protocol_v1.json";ENTITLED_CONTRACT=ROOT/"config"/"jnu_exact_micro_entitled_source_adapter_contract_v1.json";ROLL=ROOT/"config"/"jnu_exact_micro_contract_roll_calendar_v1.json"
def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict):raise RuntimeError(f"{p} must contain an object")
    return x
def dt(s:str)->datetime:
    x=datetime.fromisoformat(str(s))
    if x.tzinfo is None:raise RuntimeError("timestamp must be offset-aware")
    return x
def run_decision(di:dict,work:Path)->dict:
    inp=work/"decision_input.json";out=work/"decision_trace.json";inp.write_text(json.dumps(di,ensure_ascii=False,indent=2)+"\n")
    cp=subprocess.run([sys.executable,str(DECISION),"--input",str(inp),"--output",str(out)],cwd=ROOT,capture_output=True,text=True)
    if cp.returncode!=0:raise RuntimeError("decision protocol fail-closed: "+(cp.stderr or cp.stdout).strip())
    return load(out)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--request",type=Path,required=True);ap.add_argument("--private-quote-bundle",type=Path,required=True);ap.add_argument("--private-ledger-root",type=Path,required=True);ap.add_argument("--created-at-taipei");a=ap.parse_args()
    require_external(a.private_quote_bundle,"private quote bundle");require_external(a.private_ledger_root,"private ledger root")
    req=load(a.request);validate_request(req);bundle=load(a.private_quote_bundle)
    if bundle.get("artifact_class")!="JNU_PRIVATE_ENTITLED_QUOTE_BUNDLE" or bundle.get("storage_scope")!="PRIVATE_INTERNAL_ONLY" or bundle.get("public_distribution_permitted") is not False:raise RuntimeError("private quote bundle boundary invalid")
    evidence=bundle.get("raw_entitled_quote_evidence")
    if not isinstance(evidence,dict):raise RuntimeError("private quote evidence missing")
    request_sha=canonical_text_sha256(a.request);fid="JNU_PRIV_LS_"+hashlib.sha256(str(req["request_id"]).encode()).hexdigest()[:24]
    out=a.private_ledger_root.resolve()/"forecasts"/f"{fid}.json"
    if out.exists():
        if verify_backup(a.private_ledger_root,out).get("status")!="PASS":raise RuntimeError("existing private forecast backup integrity invalid")
        old=load(out)
        if old.get("request_record_sha256")!=request_sha or old.get("private_quote_receipt_id")!=bundle.get("receipt_id"):raise RuntimeError("PRIVATE_FORECAST_IDEMPOTENCY_CONFLICT")
        print(json.dumps({"status":"PRIVATE_ENTITLED_FORECAST_ALREADY_REGISTERED","forecast_id":fid,"raw_and_derived_fields_not_printed":True,"public_output_created":False,"real_public_ledger_modified":False},indent=2));return
    qv=validate_entitled_quote(evidence,load(ENTITLED_CONTRACT),load(ROLL))
    if str(evidence["canonical_symbol"]).upper()!=str(req["symbol"]).upper():raise RuntimeError("private entitled quote symbol mismatch request")
    created=dt(a.created_at_taipei).astimezone(TAIPEI) if a.created_at_taipei else datetime.now(TAIPEI);rc=dt(req["request_created_at_taipei"]).astimezone(TAIPEI);ru=dt(req["request_valid_until_taipei"]).astimezone(TAIPEI)
    if created<rc or created>ru:raise RuntimeError("private forecast creation outside immutable request window")
    ref=dt(evidence["provider_timestamp"]).astimezone(TAIPEI);age=(created-ref).total_seconds()
    if age<0 or age>900:raise RuntimeError(f"private entitled quote stale at forecast creation: age={age:.3f}")
    import tempfile
    with tempfile.TemporaryDirectory(prefix="jnu_private_decision_") as td:trace=run_decision(req["decision_input"],Path(td))
    prepared=validate_prepared_request_binding(req,decision_event_state=(trace.get("risk_modifiers") or {}).get("event_state"));risk=validate_risk_state_evidence(req["risk_state_evidence"],trace,created.isoformat(),request_created_at=req["request_created_at_taipei"],target_day_session_date=req["target_day_session_date"])
    record={"version":"1.1","artifact_class":"JNU_PRIVATE_ENTITLED_FORECAST","forecast_id":fid,"storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"request_id":req["request_id"],"request_record_sha256":request_sha,"draft_id":req["draft_id"],"request_created_at_taipei":rc.isoformat(),"analysis_frozen_at_taipei":req["analysis_frozen_at_taipei"],"request_valid_until_taipei":ru.isoformat(),"symbol":str(req["symbol"]).upper(),"created_at_taipei":created.isoformat(),"reference_price":float(evidence["price"]),"reference_timestamp":ref.isoformat(),"entitlement_mode":evidence["entitlement_mode"],"provider_name":evidence["provider_name"],"private_quote_receipt_id":bundle["receipt_id"],"entitled_quote_evidence":evidence,"entitled_quote_validation":qv,"reference_age_seconds_at_forecast":age,"exact_product":True,"target_day_session_date":req["target_day_session_date"],"bias":trace["bias"],"confidence":trace["confidence"],"decision_trace":trace,"risk_state_evidence":req["risk_state_evidence"],"risk_state_evidence_validation":risk,"request_preparation":req["request_preparation"],"request_preparation_validation":prepared,"expected_path":req["expected_path"],"key_levels":req["key_levels"],"invalidation_conditions":req["invalidation_conditions"],"event_risk":req["event_risk"],"flip_conditions":req["flip_conditions"],"evidence_summary":req["evidence_summary"],"framework_sha256":canonical_text_sha256(FRAMEWORK),"shadow_prereg_sha256":canonical_text_sha256(PREREG),"implementation_sha256":canonical_text_sha256(IMPL),"decision_protocol_sha256":canonical_text_sha256(PROTOCOL),"integrity_hash_protocol_sha256":canonical_text_sha256(HASH_PROTOCOL),"cloud_request_protocol_sha256":canonical_text_sha256(REQUEST_PROTOCOL),"request_preparation_protocol_sha256":canonical_text_sha256(PREP_PROTOCOL),"official_event_state_protocol_sha256":canonical_text_sha256(EVENT_PROTOCOL),"analysis_draft_protocol_sha256":canonical_text_sha256(DRAFT_PROTOCOL),"immutable_record":True,"outcome_known_at_registration":False,"public_output_created":False}
    write_immutable_json(a.private_ledger_root,out,record)
    print(json.dumps({"status":"PRIVATE_ENTITLED_FORECAST_REGISTERED","forecast_id":fid,"raw_and_derived_fields_not_printed":True,"public_output_created":False,"real_public_ledger_modified":False},indent=2))
if __name__=="__main__":main()
