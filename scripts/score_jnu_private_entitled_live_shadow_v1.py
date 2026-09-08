from __future__ import annotations
import argparse, json, os, statistics
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external,verify_backup,write_replace_json,sha256_file
from jnu_integrity_hash_v1 import canonical_text_sha256
from jnu_request_preparation_validation_v1_1 import validate_prepared_request_binding
from jnu_risk_state_evidence_validation_v1_2 import validate_risk_state_evidence
from score_jnu_operational_live_shadow_v1_6 import recompute_trace, bootstrap
from validate_jnu_entitled_exact_micro_evidence_v1 import validate as validate_entitled_quote

ROOT=Path(__file__).resolve().parents[1]
FRAMEWORK=ROOT/"config"/"jnu_operational_framework_current_v1_9.json"
PREREG=ROOT/"config"/"jnu_operational_live_shadow_prereg_v1_7.json"
IMPL=ROOT/"config"/"jnu_operational_live_shadow_implementation_v1_7.json"
PROTOCOL=ROOT/"config"/"jnu_operational_decision_protocol_v1.json"
CONTRACT=ROOT/"config"/"jnu_exact_micro_entitled_source_adapter_contract_v1.json"
ROLL=ROOT/"config"/"jnu_exact_micro_contract_roll_calendar_v1.json"

def load(p:Path)->dict:return json.loads(p.read_text(encoding="utf-8"))
def outside(p:Path,label:str): require_external(p,label)
def close(a,b,tol=1e-14):return abs(float(a)-float(b))<=tol

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--private-ledger-root",type=Path,required=True);ap.add_argument("--output",type=Path);a=ap.parse_args()
    outside(a.private_ledger_root,"private ledger root")
    out=a.output or (a.private_ledger_root.resolve()/"results"/"private_live_shadow_current_v1.json");outside(out,"private score output")
    protocol=load(PROTOCOL);forecasts={};fps={}
    fd=a.private_ledger_root.resolve()/"forecasts";od=a.private_ledger_root.resolve()/"outcomes"
    for p in sorted(fd.glob("*.json")) if fd.exists() else []:
        if verify_backup(a.private_ledger_root,p).get("status")!="PASS":raise RuntimeError(f"private forecast backup integrity invalid: {p.name}")
        f=load(p);fid=f.get("forecast_id")
        if fid!=p.stem:raise RuntimeError("private forecast id/filename mismatch")
        if f.get("artifact_class")!="JNU_PRIVATE_ENTITLED_FORECAST" or f.get("storage_scope")!="PRIVATE_INTERNAL_ONLY":raise RuntimeError(f"private forecast {fid} class/storage invalid")
        if f.get("framework_sha256")!=canonical_text_sha256(FRAMEWORK):raise RuntimeError(f"private forecast {fid} framework SHA mismatch")
        if f.get("shadow_prereg_sha256")!=canonical_text_sha256(PREREG) or f.get("implementation_sha256")!=canonical_text_sha256(IMPL):raise RuntimeError(f"private forecast {fid} prereg/implementation SHA mismatch")
        e=f.get("entitled_quote_evidence");qv=validate_entitled_quote(e,load(CONTRACT),load(ROLL))
        if f.get("entitled_quote_validation")!=qv:raise RuntimeError(f"private forecast {fid} quote validation mismatch")
        if not close(f["reference_price"],e["price"]) or str(f["reference_timestamp"])!=__import__("datetime").datetime.fromisoformat(str(e["provider_timestamp"])).astimezone(__import__("datetime").timezone(__import__("datetime").timedelta(hours=8))).isoformat():raise RuntimeError(f"private forecast {fid} reference/evidence mismatch")
        tr=f.get("decision_trace");rc=recompute_trace(tr,protocol)
        for k in ["bias","confidence","eligible_directional_blocks","bullish_blocks","bearish_blocks","net_directional_score","event_forced_abstain"]:
            if tr.get(k)!=rc[k]:raise RuntimeError(f"private forecast {fid} trace mismatch {k}")
        if tr.get("quality_a_counts")!=rc["quality_a_counts"] or f.get("bias")!=rc["bias"] or f.get("confidence")!=rc["confidence"]:raise RuntimeError(f"private forecast {fid} top-level decision mismatch")
        pv=validate_prepared_request_binding(f,decision_event_state=(tr.get("risk_modifiers") or {}).get("event_state"))
        if f.get("request_preparation_validation")!=pv:raise RuntimeError(f"private forecast {fid} request validation mismatch")
        rv=validate_risk_state_evidence(f["risk_state_evidence"],tr,f["created_at_taipei"],request_created_at=f["request_created_at_taipei"],target_day_session_date=f["target_day_session_date"])
        if f.get("risk_state_evidence_validation")!=rv:raise RuntimeError(f"private forecast {fid} risk validation mismatch")
        forecasts[fid]=f;fps[fid]=p
    rows=[]
    for p in sorted(od.glob("*.json")) if od.exists() else []:
        if verify_backup(a.private_ledger_root,p).get("status")!="PASS":raise RuntimeError(f"private outcome backup integrity invalid: {p.name}")
        o=load(p);fid=o.get("forecast_id")
        if fid!=p.stem or fid not in forecasts:raise RuntimeError("private outcome id/forecast mismatch")
        if o.get("artifact_class")!="JNU_PRIVATE_ENTITLED_OUTCOME" or o.get("storage_scope")!="PRIVATE_INTERNAL_ONLY":raise RuntimeError(f"private outcome {fid} class/storage invalid")
        if o.get("forecast_record_sha256")!=canonical_text_sha256(fps[fid]):raise RuntimeError(f"private outcome {fid} forecast hash mismatch")
        e=o.get("entitled_close_evidence");qv=validate_entitled_quote(e,load(CONTRACT),load(ROLL))
        if o.get("entitled_close_validation")!=qv:raise RuntimeError(f"private outcome {fid} close validation mismatch")
        f=forecasts[fid];ret=float(o["target_close_price"])/float(f["reference_price"])-1.0
        bias=f["bias"]
        if bias=="BULLISH":signed=ret;hit=True if ret>0 else (False if ret<0 else None)
        elif bias=="BEARISH":signed=-ret;hit=True if ret<0 else (False if ret>0 else None)
        else:signed=None;hit=None
        if not close(ret,o["outcome_return"]):raise RuntimeError(f"private outcome {fid} return mismatch")
        if signed is None:
            if o.get("signed_outcome_return") is not None:raise RuntimeError(f"private outcome {fid} signed return mismatch")
        elif not close(signed,o["signed_outcome_return"]):raise RuntimeError(f"private outcome {fid} signed return mismatch")
        if o.get("directional_hit")!=hit:raise RuntimeError(f"private outcome {fid} hit mismatch")
        rows.append({"forecast_id":fid,"bias":bias,"confidence":f["confidence"],"outcome_return":ret,"signed_outcome_return":signed,"directional_hit":hit})
    scored=[r for r in rows if r["bias"]!="NEUTRAL_ABSTAIN"];signed=[float(r["signed_outcome_return"]) for r in scored];hits=[r["directional_hit"] for r in scored if r["directional_hit"] is not None]
    b=bootstrap(signed) if signed else None;n=len(scored);acc=sum(bool(x) for x in hits)/len(hits) if hits else None
    gate={"minimum_30_nonabstain":n>=30,"directional_accuracy_gt_0_50":acc>0.5 if acc is not None else False,"mean_signed_return_positive":statistics.fmean(signed)>0 if signed else False,"bootstrap_prob_mean_positive_ge_0_90":b is not None and b["prob_mean_positive"]>=0.90}
    status="PRIVATE_LIVE_SHADOW_FIRST_REVIEW_PASS" if n>=30 and all(gate.values()) else ("PRIVATE_LIVE_SHADOW_FIRST_REVIEW_FAIL" if n>=30 else "PRIVATE_LIVE_SHADOW_ACCUMULATING")
    result={"version":"1.0","status":status,"artifact_class":"JNU_PRIVATE_ENTITLED_LIVE_SHADOW_SCORE","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,
      "integrity":{"status":"PASS","forecasts_verified":len(forecasts),"outcomes_verified":len(rows),"decision_trace_recomputed":True,"risk_state_evidence_recomputed":True,"request_preparation_recomputed":True,"entitled_quote_recomputed":True,"outcome_recomputed":True},
      "framework_sha256":canonical_text_sha256(FRAMEWORK),"forecast_records":len(forecasts),"outcomes_recorded":len(rows),"nonabstain_scored":n,
      "directional_accuracy":acc,"mean_signed_return":statistics.fmean(signed) if signed else None,"bootstrap":b,"first_review_gate":gate,"rows":rows}
    out.parent.mkdir(parents=True,exist_ok=True);score_sha=write_replace_json(out,result)
    checkpoint={"version":"1.0","artifact_class":"JNU_PRIVATE_ENTITLED_SCORER_CHECKPOINT","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"score_record_sha256":score_sha,"forecast_records":len(forecasts),"outcomes_recorded":len(rows),"integrity_status":"PASS"}
    write_replace_json(out.parent/"private_live_shadow_checkpoint_v1.json",checkpoint)
    print(json.dumps({"status":"PRIVATE_ENTITLED_SCORER_COMPLETED","private_result_written":True,"raw_and_derived_metrics_not_printed":True,"public_output_created":False},indent=2))
if __name__=="__main__":main()
