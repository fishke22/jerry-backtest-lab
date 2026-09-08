from __future__ import annotations
import copy, hashlib, json, shutil, tempfile
from pathlib import Path
from execute_jnu_private_selection_transaction_noop_v1 import ROOT, process, evaluate_request, load, sha256_file
from jnu_private_atomic_io_v1 import write_immutable_json

SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json";KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json";TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json";MEMORY=ROOT/"config"/"jnu_operational_framework_cross_session_memory_v1.json"
def w(p:Path,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+"\n",encoding="utf-8")
def rejected(fn):
    try:fn();return False
    except Exception:return True
short=load(SHORTLIST);pair=short["market_data_candidates"][0]["id"]+"__"+short["key_custody_candidates"][0]["id"];pid,kid=pair.split("__",1);T={}
before={p:sha256_file(p) for p in [SHORTLIST,KEY_CURRENT,TERMS_CURRENT]}
with tempfile.TemporaryDirectory(prefix="jnu-tx-noop-") as td0:
    td=Path(td0);ds=td/"ds";ps=td/"ps";cs=td/"cs";ts=td/"ts"
    for p in [ds,ps,cs,ts]:p.mkdir()
    d={"version":"1.0","artifact_class":"JNU_SYNTHETIC_SELECTION_DECISION_LIFECYCLE_CURRENT_AUTH_RECORD","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"mode":"SYNTHETIC","status":"SYNTHETIC_LIFECYCLE_CURRENT_AUTH_VALIDATED_NO_SELECTION","decision_id":"D","requested_combination_id":pair,"requested_market_data_candidate_id":pid,"requested_kms_candidate_id":kid,"lifecycle_event_count":3,"lifecycle_head_sha256":hashlib.sha256(b"h").hexdigest(),"selection_transition_permitted":False,"selection_written":False,"selected_combination_id":"UNSELECTED","production_state_mutated":False,"real_activation_authorized":False}
    dp=ds/"selection_lifecycle_decisions"/"d.json";write_immutable_json(ds,dp,d)
    cas={"PROVIDER_SELECTION_SHORTLIST":{"path":"config/jnu_provider_selection_shortlist_v1.json","sha256":sha256_file(SHORTLIST)},"PRODUCTION_KEY_CUSTODY_CURRENT":{"path":"config/jnu_production_key_custody_current_v1.json","sha256":sha256_file(KEY_CURRENT)},"PROVIDER_TERM_READINESS_CURRENT":{"path":"config/jnu_provider_term_readiness_current_v1.json","sha256":sha256_file(TERMS_CURRENT)}}
    c={"version":"1.0","artifact_class":"JNU_SYNTHETIC_SELECTION_TRANSITION_PREPARE_CHANGESET","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"mode":"SYNTHETIC","status":"SYNTHETIC_PREPARE_ONLY_CHANGESET_READY_NOT_COMMITTABLE","prepare_id":"P","decision_id":"D","decision_record_sha256":sha256_file(dp),"requested_combination_id":pair,"requested_market_data_candidate_id":pid,"requested_kms_candidate_id":kid,"lifecycle_event_count":3,"lifecycle_head_sha256":d["lifecycle_head_sha256"],"production_state_preconditions":cas,"commit_capability":False,"apply_capability":False,"selection_transition_permitted":False,"selection_written":False,"selected_combination_id":"UNSELECTED","production_state_mutated":False,"real_activation_authorized":False}
    cp=ps/"selection_transition_prepares"/"p.json";write_immutable_json(ps,cp,c)
    flat={k:v["sha256"] for k,v in cas.items()}
    ceremony={"version":"1.0","artifact_class":"JNU_REDACTED_SYNTHETIC_COMMIT_AUTHORIZATION_CEREMONY_RECEIPT","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"mode":"SYNTHETIC","status":"SYNTHETIC_COMMIT_AUTHORIZATION_CEREMONY_VALIDATED_DISABLED_NO_EXECUTION","ceremony_id":"C","authorization_status":"SYNTHETIC_DISABLED","changeset_sha256":sha256_file(cp),"prepare_id":"P","decision_id":"D","decision_record_sha256":sha256_file(dp),"requested_combination_id":pair,"requested_market_data_candidate_id":pid,"requested_kms_candidate_id":kid,"lifecycle_event_count":3,"lifecycle_head_sha256":d["lifecycle_head_sha256"],"production_state_cas_sha256":flat,"commit_authorized":False,"apply_authorized":False,"execution_capability":False,"selection_transition_permitted":False,"selection_written":False,"selected_combination_id":"UNSELECTED","production_state_mutated":False,"real_activation_authorized":False}
    cr=cs/"commit_authorization_ceremonies"/"c.json";write_immutable_json(cs,cr,ceremony)
    req={"version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,"operation":"NOOP_DRY_RUN","transaction_id":"JNU_SELECTION_TX_NOOP_SYNTH_001","evaluated_at_utc":"2026-09-09T00:00:00+00:00","ceremony_store_root":str(cs.resolve()),"ceremony_receipt_path":str(cr.resolve()),"ceremony_receipt_sha256":sha256_file(cr),"prepare_store_root":str(ps.resolve()),"changeset_path":str(cp.resolve()),"changeset_sha256":sha256_file(cp),"decision_store_root":str(ds.resolve()),"decision_record_path":str(dp.resolve()),"decision_record_sha256":sha256_file(dp)}
    rp=td/"req.json";w(rp,req);o=process(rp,ts);tr=ts/"selection_transaction_noop_receipts"/(req["transaction_id"]+".json");x=load(tr)
    T["baseline_noop_receipt_written"]=o["status"]=="NOOP_TRANSACTION_RECEIPT_WRITTEN"
    T["execution_blocked_disabled"]=x["status"]=="EXECUTION_BLOCKED_DISABLED_AUTHORIZATION"
    T["exact_seven_step_sequence"]=[s["step"] for s in x["transaction_sequence"]]==["LOCK_ACQUISITION","CAS_VERIFICATION","PRIVATE_PREIMAGE_BACKUP","MUTATION_SET","POST_WRITE_VERIFICATION","ROLLBACK_ON_PARTIAL_FAILURE","FINAL_TRANSACTION_RECEIPT"]
    T["only_cas_executes_read_only"]=x["transaction_sequence"][1]["status"]=="EXECUTED_READ_ONLY" and all(not s["production_effect"] for s in x["transaction_sequence"])
    T["no_lock_backup_mutation"]=x["lock_acquired"] is False and x["production_preimage_backup_created"] is False and x["mutation_attempted"] is False and x["mutation_applied"] is False
    T["no_postwrite_or_rollback"]=x["post_write_verification_performed"] is False and x["rollback_performed"] is False
    T["lineage_bound"]=x["ceremony_receipt_sha256"]==sha256_file(cr) and x["changeset_sha256"]==sha256_file(cp) and x["decision_record_sha256"]==sha256_file(dp)
    T["cas_all_three_match"]=set(x["production_state_cas_verification"])=={"PROVIDER_SELECTION_SHORTLIST","PRODUCTION_KEY_CUSTODY_CURRENT","PROVIDER_TERM_READINESS_CURRENT"} and all(v["match"] for v in x["production_state_cas_verification"].values())
    T["selection_activation_false"]=x["selection_written"] is False and x["production_state_mutated"] is False and x["real_activation_authorized"] is False
    T["exact_replay_idempotent"]=process(rp,ts)["status"]=="IDEMPOTENT_REPLAY_ACCEPTED"

    for op,name in [("COMMIT","commit_operation_rejected"),("APPLY","apply_operation_rejected"),("EXECUTE","execute_operation_rejected"),("MUTATE","mutate_operation_rejected"),("ROLLBACK","rollback_operation_rejected")]:
        q=copy.deepcopy(req);q["operation"]=op;T[name]=rejected(lambda q=q:evaluate_request(q))
    q=copy.deepcopy(req);q["mode"]="REAL";T["real_mode_rejected"]=rejected(lambda:evaluate_request(q))
    q=copy.deepcopy(req);q["mutation_payload"]={"x":1};T["mutation_payload_rejected"]=rejected(lambda:evaluate_request(q))
    for field,name in [("ceremony_receipt_sha256","wrong_ceremony_hash_rejected"),("changeset_sha256","wrong_changeset_hash_rejected"),("decision_record_sha256","wrong_decision_hash_rejected")]:
        q=copy.deepcopy(req);q[field]="0"*64;T[name]=rejected(lambda q=q:evaluate_request(q))

    def badcer(mut,name):
        root=td/name;root.mkdir();z=copy.deepcopy(ceremony);mut(z);p=root/"commit_authorization_ceremonies"/"c.json";write_immutable_json(root,p,z);q=copy.deepcopy(req);q["ceremony_store_root"]=str(root.resolve());q["ceremony_receipt_path"]=str(p.resolve());q["ceremony_receipt_sha256"]=sha256_file(p);T[name]=rejected(lambda:evaluate_request(q))
    badcer(lambda z:z.__setitem__("commit_authorized",True),"enabled_commit_ceremony_rejected")
    badcer(lambda z:z.__setitem__("apply_authorized",True),"enabled_apply_ceremony_rejected")
    badcer(lambda z:z.__setitem__("execution_capability",True),"enabled_execution_ceremony_rejected")
    badcer(lambda z:z.__setitem__("authorization_status","SYNTHETIC_ENABLED"),"enabled_status_ceremony_rejected")
    badcer(lambda z:z.__setitem__("requested_combination_id","OTHER"),"pair_substitution_rejected")
    badcer(lambda z:z.__setitem__("lifecycle_event_count",4),"lifecycle_count_mismatch_rejected")
    badcer(lambda z:z.__setitem__("lifecycle_head_sha256","0"*64),"lifecycle_head_mismatch_rejected")
    badcer(lambda z:z.__setitem__("production_state_cas_sha256",{**flat,"PROVIDER_SELECTION_SHORTLIST":"0"*64}),"ceremony_cas_mismatch_rejected")

    # Primary artifact tamper must fail immutable backup verification.
    for base,sub,filep,prefix,name,keyroot,keypath,keysha in [
      (cs,"commit_authorization_ceremonies",cr,"tamc","ceremony_tamper_rejected","ceremony_store_root","ceremony_receipt_path","ceremony_receipt_sha256"),
      (ps,"selection_transition_prepares",cp,"tamp","changeset_tamper_rejected","prepare_store_root","changeset_path","changeset_sha256"),
      (ds,"selection_lifecycle_decisions",dp,"tamd","decision_tamper_rejected","decision_store_root","decision_record_path","decision_record_sha256")]:
        root=td/prefix;shutil.copytree(base,root);p=root/sub/filep.name;z=load(p);z["status"]="TAMPERED";w(p,z);q=copy.deepcopy(req);q[keyroot]=str(root.resolve());q[keypath]=str(p.resolve());q[keysha]=sha256_file(p);T[name]=rejected(lambda q=q:evaluate_request(q))

    # Same transaction ID with distinct valid external ceremony conflicts immutably.
    cs2=td/"cs2";cs2.mkdir();c2=copy.deepcopy(ceremony);c2["ceremony_id"]="C2";p2=cs2/"commit_authorization_ceremonies"/"c2.json";write_immutable_json(cs2,p2,c2);q=copy.deepcopy(req);q["ceremony_store_root"]=str(cs2.resolve());q["ceremony_receipt_path"]=str(p2.resolve());q["ceremony_receipt_sha256"]=sha256_file(p2);q2=td/"q2.json";w(q2,q)
    T["same_transaction_id_different_content_rejected"]=rejected(lambda:process(q2,ts))
    T["repo_internal_request_rejected"]=rejected(lambda:process(ROOT/"config/jnu_private_selection_transition_commit_authorization_checkpoint_v1.json",ts))
    T["repo_internal_transaction_store_rejected"]=rejected(lambda:process(rp,ROOT/"tx-noop-store-forbidden"))

after={p:sha256_file(p) for p in [SHORTLIST,KEY_CURRENT,TERMS_CURRENT]};T["production_state_files_byte_identical"]=before==after
short2=load(SHORTLIST);key=load(KEY_CURRENT);terms=load(TERMS_CURRENT);mem=load(MEMORY)
T["shortlist_still_unselected"]=short2["selected_market_data_provider"]=="UNSELECTED" and short2["selected_key_custody_provider"]=="UNSELECTED"
T["production_key_still_disabled_unselected"]=key["production_enabled"] is False and key["vendor"]=="UNSELECTED" and key["region"]=="UNSELECTED"
T["provider_terms_boundary_unchanged"]=terms["broker_auth_used"] is False and terms["trading_permission_used"] is False and terms["public_output_requested"] is False
T["public_real_ledger_still_zero_zero"]=mem.get("real_live_shadow_forecasts_registered")==0 and mem.get("real_live_shadow_outcomes_registered")==0
status="PASS" if all(T.values()) else "FAIL"
print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T)},indent=2));raise SystemExit(0 if status=="PASS" else 1)
