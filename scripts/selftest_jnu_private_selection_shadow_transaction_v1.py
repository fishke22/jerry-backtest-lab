from __future__ import annotations
import copy, hashlib, json, tempfile
from pathlib import Path
from simulate_jnu_private_selection_shadow_transaction_v1 import ROOT, process, load, sha256_file
from jnu_private_atomic_io_v1 import write_immutable_json

SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json";KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json";TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json";MEMORY=ROOT/"config"/"jnu_operational_framework_cross_session_memory_v1.json"
def w(p:Path,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+"\n",encoding="utf-8")
def rejected(fn):
    try:fn();return False
    except Exception:return True

prod=[SHORTLIST,KEY_CURRENT,TERMS_CURRENT];before={p:p.read_bytes() for p in prod};short=load(SHORTLIST);pid=short["market_data_candidates"][0]["id"];kid=short["key_custody_candidates"][0]["id"];pair=pid+"__"+kid;T={}
with tempfile.TemporaryDirectory(prefix="jnu-shadow-sim-") as td0:
    td=Path(td0);ds=td/"ds";ps=td/"ps";ns=td/"ns";receipts=td/"receipts"
    for p in [ds,ps,ns,receipts]:p.mkdir()
    d={"version":"1.0","artifact_class":"JNU_SYNTHETIC_SELECTION_DECISION_LIFECYCLE_CURRENT_AUTH_RECORD","status":"SYNTHETIC_LIFECYCLE_CURRENT_AUTH_VALIDATED_NO_SELECTION","decision_id":"D","requested_combination_id":pair,"requested_market_data_candidate_id":pid,"requested_kms_candidate_id":kid,"lifecycle_event_count":3,"lifecycle_head_sha256":hashlib.sha256(b"h").hexdigest()}
    dp=ds/"selection_lifecycle_decisions"/"d.json";write_immutable_json(ds,dp,d)
    cas={"PROVIDER_SELECTION_SHORTLIST":{"path":"config/jnu_provider_selection_shortlist_v1.json","sha256":sha256_file(SHORTLIST)},"PRODUCTION_KEY_CUSTODY_CURRENT":{"path":"config/jnu_production_key_custody_current_v1.json","sha256":sha256_file(KEY_CURRENT)},"PROVIDER_TERM_READINESS_CURRENT":{"path":"config/jnu_provider_term_readiness_current_v1.json","sha256":sha256_file(TERMS_CURRENT)}}
    c={"version":"1.0","artifact_class":"JNU_SYNTHETIC_SELECTION_TRANSITION_PREPARE_CHANGESET","status":"SYNTHETIC_PREPARE_ONLY_CHANGESET_READY_NOT_COMMITTABLE","prepare_id":"P","decision_id":"D","decision_record_sha256":sha256_file(dp),"requested_combination_id":pair,"requested_market_data_candidate_id":pid,"requested_kms_candidate_id":kid,"lifecycle_event_count":3,"lifecycle_head_sha256":d["lifecycle_head_sha256"],"production_state_preconditions":cas}
    cp=ps/"selection_transition_prepares"/"p.json";write_immutable_json(ps,cp,c)
    n={"version":"1.0","artifact_class":"JNU_SYNTHETIC_SELECTION_TRANSACTION_NOOP_RECEIPT","status":"EXECUTION_BLOCKED_DISABLED_AUTHORIZATION","transaction_id":"N","changeset_sha256":sha256_file(cp),"decision_id":"D","decision_record_sha256":sha256_file(dp),"requested_combination_id":pair,"requested_market_data_candidate_id":pid,"requested_kms_candidate_id":kid,"lifecycle_event_count":3,"lifecycle_head_sha256":d["lifecycle_head_sha256"],"commit_authorized":False,"apply_authorized":False,"execution_capability":False,"production_state_mutated":False}
    np=ns/"selection_transaction_noop_receipts"/"n.json";write_immutable_json(ns,np,n)

    def req(sim,fault="NONE",cond="NONE"):
        return {"version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,"operation":"SHADOW_FAULT_SIMULATION","simulation_id":sim,"evaluated_at_utc":"2026-09-09T01:00:00+00:00","fault_at":fault,"test_condition":cond,"noop_store_root":str(ns.resolve()),"noop_receipt_path":str(np.resolve()),"noop_receipt_sha256":sha256_file(np),"prepare_store_root":str(ps.resolve()),"changeset_path":str(cp.resolve()),"changeset_sha256":sha256_file(cp),"decision_store_root":str(ds.resolve()),"decision_record_path":str(dp.resolve()),"decision_record_sha256":sha256_file(dp),"shadow_root":str((td/("shadow-"+sim)).resolve())}
    def run(sim,fault="NONE",cond="NONE"):
        q=req(sim,fault,cond);p=td/(sim+".json");w(p,q);r=process(p,receipts);rp=receipts/"selection_shadow_simulation_receipts"/(sim+".json");return r,load(rp),p

    r,x,p=run("JNU_SELECTION_SHADOW_SIM_SYNTH_BASE")
    T["baseline_success"]=x["status"]=="SHADOW_TRANSACTION_SIMULATED_SUCCESS_PRODUCTION_UNCHANGED"
    T["seven_steps_exact"]=[s["step"] for s in x["transaction_sequence"]]==["LOCK_ACQUISITION","CAS_VERIFICATION","PRIVATE_PREIMAGE_BACKUP","MUTATION_SET","POST_WRITE_VERIFICATION","ROLLBACK_ON_PARTIAL_FAILURE","FINAL_TRANSACTION_RECEIPT"]
    T["baseline_shadow_mutated"]=x["shadow_final_sha256"]!=x["shadow_preimage_sha256"]
    T["baseline_no_rollback"]=x["rollback_performed"] is False
    T["production_before_after_equal"]=x["production_unchanged"] is True and x["production_sha256_before"]==x["production_sha256_after"]
    T["real_capabilities_false"]=x["real_commit_capability"] is False and x["real_apply_capability"] is False and x["production_state_mutated"] is False
    T["exact_replay_idempotent"]=process(p,receipts)["status"]=="IDEMPOTENT_REPLAY_ACCEPTED"

    expected_fault_status={
      "LOCK_ACQUISITION":"SHADOW_FAULT_INJECTED_NO_PRODUCTION_EFFECT",
      "CAS_VERIFICATION":"SHADOW_FAULT_INJECTED_NO_PRODUCTION_EFFECT",
      "PRIVATE_PREIMAGE_BACKUP":"SHADOW_FAULT_INJECTED_NO_PRODUCTION_EFFECT",
      "MUTATION_SET":"SHADOW_FAULT_INJECTED_ROLLED_BACK_PRODUCTION_UNCHANGED",
      "POST_WRITE_VERIFICATION":"SHADOW_FAULT_INJECTED_ROLLED_BACK_PRODUCTION_UNCHANGED",
      "ROLLBACK_ON_PARTIAL_FAILURE":"SHADOW_FAULT_INJECTED_ROLLED_BACK_PRODUCTION_UNCHANGED",
      "FINAL_TRANSACTION_RECEIPT":"SHADOW_FAULT_INJECTED_ROLLED_BACK_PRODUCTION_UNCHANGED"
    }
    fault_receipts={}
    for i,(fault,status) in enumerate(expected_fault_status.items(),1):
        _,fx,_=run(f"JNU_SELECTION_SHADOW_SIM_SYNTH_FAULT_{i}",fault)
        fault_receipts[fault]=fx
        T["fault_"+fault+"_status"]=fx["status"]==status
        T["fault_"+fault+"_production_unchanged"]=fx["production_unchanged"] is True and fx["production_state_mutated"] is False
    T["mutation_fault_rolls_back_exact"]=fault_receipts["MUTATION_SET"]["shadow_final_sha256"]==fault_receipts["MUTATION_SET"]["shadow_preimage_sha256"] and fault_receipts["MUTATION_SET"]["rollback_performed"] is True
    T["postwrite_fault_rolls_back_exact"]=fault_receipts["POST_WRITE_VERIFICATION"]["shadow_final_sha256"]==fault_receipts["POST_WRITE_VERIFICATION"]["shadow_preimage_sha256"]
    T["rollback_fault_resumes_and_restores"]=fault_receipts["ROLLBACK_ON_PARTIAL_FAILURE"]["rollback_interruption_resumed"] is True and fault_receipts["ROLLBACK_ON_PARTIAL_FAILURE"]["shadow_final_sha256"]==fault_receipts["ROLLBACK_ON_PARTIAL_FAILURE"]["shadow_preimage_sha256"]
    T["final_receipt_fault_rolls_back"]=fault_receipts["FINAL_TRANSACTION_RECEIPT"]["rollback_performed"] is True and fault_receipts["FINAL_TRANSACTION_RECEIPT"]["shadow_final_sha256"]==fault_receipts["FINAL_TRANSACTION_RECEIPT"]["shadow_preimage_sha256"]

    _,stale,_=run("JNU_SELECTION_SHADOW_SIM_SYNTH_STALE","NONE","STALE_SHADOW_CAS")
    T["stale_shadow_cas_blocked"]=stale["status"]=="SHADOW_STALE_CAS_BLOCKED_PRODUCTION_UNCHANGED"
    T["stale_shadow_never_backed_or_mutated"]=any(s["step"]=="PRIVATE_PREIMAGE_BACKUP" and s["status"]=="NOT_REACHED" for s in stale["transaction_sequence"])
    _,corrupt,_=run("JNU_SELECTION_SHADOW_SIM_SYNTH_CORRUPT","NONE","CORRUPT_PREIMAGE_BACKUP")
    T["corrupt_backup_blocked"]=corrupt["status"]=="SHADOW_CORRUPT_PREIMAGE_BACKUP_BLOCKED_PRODUCTION_UNCHANGED"
    T["corrupt_backup_blocks_before_mutation"]=any(s["step"]=="MUTATION_SET" and s["status"]=="NOT_REACHED" for s in corrupt["transaction_sequence"])

    bad=req("JNU_SELECTION_SHADOW_SIM_SYNTH_BADMODE");bad["mode"]="REAL";bp=td/"badmode.json";w(bp,bad);T["real_mode_rejected"]=rejected(lambda:process(bp,receipts))
    bad=req("JNU_SELECTION_SHADOW_SIM_SYNTH_BADOP");bad["operation"]="COMMIT";bp=td/"badop.json";w(bp,bad);T["commit_operation_rejected"]=rejected(lambda:process(bp,receipts))
    bad=req("JNU_SELECTION_SHADOW_SIM_SYNTH_BADFAULT");bad["fault_at"]="UNKNOWN";bp=td/"badfault.json";w(bp,bad);T["unknown_fault_rejected"]=rejected(lambda:process(bp,receipts))
    bad=req("JNU_SELECTION_SHADOW_SIM_SYNTH_BADCOND");bad["test_condition"]="UNKNOWN";bp=td/"badcond.json";w(bp,bad);T["unknown_condition_rejected"]=rejected(lambda:process(bp,receipts))
    bad=req("JNU_SELECTION_SHADOW_SIM_SYNTH_BADHASH");bad["noop_receipt_sha256"]="0"*64;bp=td/"badhash.json";w(bp,bad);T["wrong_noop_hash_rejected"]=rejected(lambda:process(bp,receipts))
    bad=req("JNU_SELECTION_SHADOW_SIM_SYNTH_BADCH");bad["changeset_sha256"]="0"*64;bp=td/"badch.json";w(bp,bad);T["wrong_changeset_hash_rejected"]=rejected(lambda:process(bp,receipts))
    bad=req("JNU_SELECTION_SHADOW_SIM_SYNTH_BADDEC");bad["decision_record_sha256"]="0"*64;bp=td/"baddec.json";w(bp,bad);T["wrong_decision_hash_rejected"]=rejected(lambda:process(bp,receipts))
    bad=req("JNU_SELECTION_SHADOW_SIM_SYNTH_INTERNAL");bad["shadow_root"]=str((ROOT/"shadow-forbidden").resolve());bp=td/"internal.json";w(bp,bad);T["repo_internal_shadow_root_rejected"]=rejected(lambda:process(bp,receipts))
    bad=req("JNU_SELECTION_SHADOW_SIM_SYNTH_SECRET");bad["api_key"]="x";bp=td/"secret.json";w(bp,bad);T["secret_field_rejected"]=rejected(lambda:process(bp,receipts))

    # Same simulation id, changed request must not replay.
    collide=req("JNU_SELECTION_SHADOW_SIM_SYNTH_BASE","CAS_VERIFICATION");cp2=td/"collision.json";w(cp2,collide)
    T["same_simulation_id_different_request_rejected"]=rejected(lambda:process(cp2,receipts))
    T["repo_internal_request_rejected"]=rejected(lambda:process(ROOT/"config/jnu_private_selection_transaction_executor_noop_checkpoint_v1.json",receipts))
    T["repo_internal_receipt_store_rejected"]=rejected(lambda:process(p,ROOT/"shadow-receipt-store-forbidden"))

after={p:p.read_bytes() for p in prod};T["production_files_byte_identical"]=before==after
short2=load(SHORTLIST);key=load(KEY_CURRENT);terms=load(TERMS_CURRENT);mem=load(MEMORY)
T["shortlist_still_unselected"]=short2["selected_market_data_provider"]=="UNSELECTED" and short2["selected_key_custody_provider"]=="UNSELECTED"
T["production_key_still_disabled_unselected"]=key["production_enabled"] is False and key["vendor"]=="UNSELECTED" and key["region"]=="UNSELECTED"
T["provider_terms_boundary_unchanged"]=terms["broker_auth_used"] is False and terms["trading_permission_used"] is False and terms["public_output_requested"] is False
T["public_real_ledger_still_zero_zero"]=mem.get("real_live_shadow_forecasts_registered")==0 and mem.get("real_live_shadow_outcomes_registered")==0
status="PASS" if all(T.values()) else "FAIL"
print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T)},indent=2));raise SystemExit(0 if status=="PASS" else 1)
