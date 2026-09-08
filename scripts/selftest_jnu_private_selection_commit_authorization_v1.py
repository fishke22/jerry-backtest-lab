from __future__ import annotations
import copy, hashlib, json, shutil, tempfile
from pathlib import Path
from validate_jnu_private_selection_commit_authorization_v1 import ROOT, process, evaluate_manifest, load, sha256_file
from jnu_private_atomic_io_v1 import write_immutable_json

SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json";KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json";TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json";MEMORY=ROOT/"config"/"jnu_operational_framework_cross_session_memory_v1.json"
def w(p:Path,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+"\n",encoding="utf-8")
def rejected(fn):
    try:fn();return False
    except Exception:return True
short=load(SHORTLIST);pair=short["market_data_candidates"][0]["id"]+"__"+short["key_custody_candidates"][0]["id"];pid,kid=pair.split("__",1);T={}
before={p:sha256_file(p) for p in [SHORTLIST,KEY_CURRENT,TERMS_CURRENT]}
with tempfile.TemporaryDirectory(prefix="jnu-commit-auth-") as td0:
    td=Path(td0);ds=td/"ds";ps=td/"ps";rs=td/"rs";cs=td/"cs"
    for p in [ds,ps,rs,cs]:p.mkdir()
    d={"version":"1.0","artifact_class":"JNU_SYNTHETIC_SELECTION_DECISION_LIFECYCLE_CURRENT_AUTH_RECORD","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"mode":"SYNTHETIC","status":"SYNTHETIC_LIFECYCLE_CURRENT_AUTH_VALIDATED_NO_SELECTION","decision_id":"D","decision_at_utc":"2026-09-08T10:00:00+00:00","requested_combination_id":pair,"requested_market_data_candidate_id":pid,"requested_kms_candidate_id":kid,"lifecycle_event_count":3,"lifecycle_head_sha256":hashlib.sha256(b"h").hexdigest(),"selection_transition_permitted":False,"selection_written":False,"selected_combination_id":"UNSELECTED","production_state_mutated":False,"real_activation_authorized":False}
    dp=ds/"selection_lifecycle_decisions"/"d.json";write_immutable_json(ds,dp,d)
    cas={"PROVIDER_SELECTION_SHORTLIST":{"path":"config/jnu_provider_selection_shortlist_v1.json","sha256":sha256_file(SHORTLIST)},"PRODUCTION_KEY_CUSTODY_CURRENT":{"path":"config/jnu_production_key_custody_current_v1.json","sha256":sha256_file(KEY_CURRENT)},"PROVIDER_TERM_READINESS_CURRENT":{"path":"config/jnu_provider_term_readiness_current_v1.json","sha256":sha256_file(TERMS_CURRENT)}}
    c={"version":"1.0","artifact_class":"JNU_SYNTHETIC_SELECTION_TRANSITION_PREPARE_CHANGESET","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"mode":"SYNTHETIC","status":"SYNTHETIC_PREPARE_ONLY_CHANGESET_READY_NOT_COMMITTABLE","prepare_id":"P","decision_id":"D","decision_record_sha256":sha256_file(dp),"requested_combination_id":pair,"requested_market_data_candidate_id":pid,"requested_kms_candidate_id":kid,"lifecycle_event_count":3,"lifecycle_head_sha256":d["lifecycle_head_sha256"],"production_state_preconditions":cas,"commit_capability":False,"apply_capability":False,"selection_transition_permitted":False,"selection_written":False,"selected_combination_id":"UNSELECTED","production_state_mutated":False,"real_activation_authorized":False}
    cp=ps/"selection_transition_prepares"/"p.json";write_immutable_json(ps,cp,c)
    reviews=[{"review_id":"R1","reviewer_role":"CHANGE_REVIEWER","reviewer_ref_sha256":hashlib.sha256(b"r1").hexdigest(),"disposition":"APPROVE","reviewed_at_utc":"2026-09-08T11:00:00+00:00","revalidation_due_at_utc":"2026-09-10T11:00:00+00:00","expires_at_utc":"2026-09-11T11:00:00+00:00","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"},{"review_id":"R2","reviewer_role":"CONTROL_REVIEWER","reviewer_ref_sha256":hashlib.sha256(b"r2").hexdigest(),"disposition":"APPROVE","reviewed_at_utc":"2026-09-08T11:01:00+00:00","revalidation_due_at_utc":"2026-09-10T11:01:00+00:00","expires_at_utc":"2026-09-11T11:01:00+00:00","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"}]
    r={"version":"1.0","artifact_class":"JNU_REDACTED_SYNTHETIC_PREPARE_DUAL_CONTROL_REVIEW_RECEIPT","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"mode":"SYNTHETIC","review_batch_id":"RB","evaluation_at_utc":"2026-09-08T12:00:00+00:00","prepare_id":"P","changeset_sha256":sha256_file(cp),"decision_id":"D","decision_record_sha256":sha256_file(dp),"lifecycle_event_count":3,"lifecycle_head_sha256":d["lifecycle_head_sha256"],"requested_combination_id":pair,"requested_market_data_candidate_id":pid,"requested_kms_candidate_id":kid,"cas_revalidated_at_review":True,"cas_state_fresh":True,"review_count":2,"reviews":reviews,"reviewer_ids_emitted":False,"outcome":"SYNTHETIC_DUAL_CONTROL_APPROVED_PREPARE_NOT_COMMITTABLE","commit_capability":False,"apply_capability":False,"selection_transition_permitted":False,"selection_written":False,"selected_combination_id":"UNSELECTED","production_state_mutated":False,"real_activation_authorized":False}
    rp=rs/"prepare_review_receipts"/"r.json";write_immutable_json(rs,rp,r)
    flatcas={k:v["sha256"] for k,v in cas.items()}
    a={"version":"1.0","artifact_class":"JNU_SYNTHETIC_COMMIT_AUTHORIZATION","mode":"SYNTHETIC","synthetic_fixture":True,"authorization_id":"A1","authorization_scope":"SELECTION_TRANSITION_COMMIT","authorization_status":"SYNTHETIC_DISABLED","authorizer_role":"USER_PRINCIPAL","authorizer_reference":"synthetic-user","authorizer_attestation":"EXPLICIT_SYNTHETIC_COMMIT_AUTHORIZATION_RECORDED_DISABLED","review_receipt_sha256":sha256_file(rp),"changeset_sha256":sha256_file(cp),"decision_record_sha256":sha256_file(dp),"requested_combination_id":pair,"lifecycle_event_count":3,"lifecycle_head_sha256":d["lifecycle_head_sha256"],"production_state_cas_sha256":flatcas,"issued_at_utc":"2026-09-08T12:05:00+00:00","valid_from_utc":"2026-09-08T12:10:00+00:00","expires_at_utc":"2026-09-09T12:10:00+00:00","commit_authorized":False,"apply_authorized":False,"execution_capability":False}
    ap=td/"a.json";w(ap,a)
    m={"version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,"ceremony_id":"JNU_COMMIT_AUTH_CEREMONY_SYNTH_001","evaluation_at_utc":"2026-09-08T13:00:00+00:00","review_store_root":str(rs.resolve()),"review_receipt_path":str(rp.resolve()),"review_receipt_sha256":sha256_file(rp),"prepare_store_root":str(ps.resolve()),"changeset_path":str(cp.resolve()),"changeset_sha256":sha256_file(cp),"decision_store_root":str(ds.resolve()),"decision_record_path":str(dp.resolve()),"decision_record_sha256":sha256_file(dp),"authorization_path":str(ap.resolve()),"authorization_sha256":sha256_file(ap)}
    mp=td/"m.json";w(mp,m);o=process(mp,cs);cr=cs/"commit_authorization_ceremonies"/(m["ceremony_id"]+".json");x=load(cr);raw=cr.read_text(encoding="utf-8")
    T["baseline_ceremony_written"]=o["status"]=="SYNTHETIC_COMMIT_AUTHORIZATION_CEREMONY_RECORDED"
    T["disabled_no_execution"]=x["commit_authorized"] is False and x["apply_authorized"] is False and x["execution_capability"] is False
    T["review_and_lineage_bound"]=x["review_receipt_sha256"]==sha256_file(rp) and x["changeset_sha256"]==sha256_file(cp) and x["decision_record_sha256"]==sha256_file(dp)
    T["pair_lifecycle_bound"]=x["requested_combination_id"]==pair and x["lifecycle_event_count"]==3 and x["lifecycle_head_sha256"]==d["lifecycle_head_sha256"]
    T["cas_revalidated"]=x["cas_revalidated_at_ceremony"] is True and x["production_state_cas_sha256"]==flatcas
    T["authorizer_redacted"]="synthetic-user" not in raw and "authorizer_ref_sha256" in x
    T["selection_production_unchanged"]=x["selection_written"] is False and x["production_state_mutated"] is False and x["selected_combination_id"]=="UNSELECTED"
    T["exact_replay_idempotent"]=process(mp,cs)["status"]=="IDEMPOTENT_REPLAY_ACCEPTED"

    def badauth(mut,name):
        aa=copy.deepcopy(a);mut(aa);p=td/(name+".json");w(p,aa);mm=copy.deepcopy(m);mm["authorization_path"]=str(p.resolve());mm["authorization_sha256"]=sha256_file(p);T[name]=rejected(lambda:evaluate_manifest(mm))
    badauth(lambda z:z.__setitem__("commit_authorized",True),"commit_enabled_rejected")
    badauth(lambda z:z.__setitem__("apply_authorized",True),"apply_enabled_rejected")
    badauth(lambda z:z.__setitem__("execution_capability",True),"execution_capability_rejected")
    badauth(lambda z:z.__setitem__("authorization_status","SYNTHETIC_ENABLED"),"enabled_status_rejected")
    badauth(lambda z:z.__setitem__("authorizer_attestation","INFERRED"),"inferred_authorization_rejected")
    badauth(lambda z:z.__setitem__("authorizer_role","OTHER"),"wrong_authorizer_role_rejected")
    badauth(lambda z:z.__setitem__("review_receipt_sha256","0"*64),"auth_review_hash_binding_rejected")
    badauth(lambda z:z.__setitem__("changeset_sha256","0"*64),"auth_changeset_hash_binding_rejected")
    badauth(lambda z:z.__setitem__("decision_record_sha256","0"*64),"auth_decision_hash_binding_rejected")
    badauth(lambda z:z.__setitem__("requested_combination_id","OTHER"),"auth_pair_binding_rejected")
    badauth(lambda z:z.__setitem__("lifecycle_event_count",4),"auth_lifecycle_count_rejected")
    badauth(lambda z:z.__setitem__("lifecycle_head_sha256","0"*64),"auth_lifecycle_head_rejected")
    badauth(lambda z:z.__setitem__("production_state_cas_sha256",{**flatcas,"PROVIDER_SELECTION_SHORTLIST":"0"*64}),"auth_cas_binding_rejected")
    badauth(lambda z:z.__setitem__("expires_at_utc","2026-09-08T12:30:00+00:00"),"expired_authorization_rejected")
    badauth(lambda z:z.__setitem__("valid_from_utc","2026-09-08T14:00:00+00:00"),"not_yet_valid_authorization_rejected")
    badauth(lambda z:z.__setitem__("issued_at_utc","2026-09-08T12:05:00"),"naive_authorization_time_rejected")
    badauth(lambda z:z.__setitem__("authorizer_reference",""),"empty_authorizer_reference_rejected")

    for field,name in [("review_receipt_sha256","wrong_review_receipt_hash_rejected"),("changeset_sha256","wrong_changeset_hash_rejected"),("decision_record_sha256","wrong_decision_hash_rejected")]:
        mm=copy.deepcopy(m);mm[field]="0"*64;T[name]=rejected(lambda mm=mm:evaluate_manifest(mm))
    mm=copy.deepcopy(m);mm["evaluation_at_utc"]="2026-09-10T11:00:00+00:00";T["stale_review_receipt_rejected"]=rejected(lambda:evaluate_manifest(mm))
    mm=copy.deepcopy(m);mm["evaluation_at_utc"]="2026-09-12T00:00:00+00:00";T["expired_review_receipt_rejected"]=rejected(lambda:evaluate_manifest(mm))
    mm=copy.deepcopy(m);mm["mode"]="REAL";T["real_mode_rejected"]=rejected(lambda:evaluate_manifest(mm))
    mm=copy.deepcopy(m);mm["api_key"]="x";T["secret_field_rejected"]=rejected(lambda:evaluate_manifest(mm))

    # Non-approved receipt rejected.
    rs2=td/"rs2";rs2.mkdir();rr=copy.deepcopy(r);rr["outcome"]="SYNTHETIC_DUAL_CONTROL_REJECTED_PREPARE";rrp=rs2/"prepare_review_receipts"/"rr.json";write_immutable_json(rs2,rrp,rr)
    mm=copy.deepcopy(m);mm["review_store_root"]=str(rs2.resolve());mm["review_receipt_path"]=str(rrp.resolve());mm["review_receipt_sha256"]=sha256_file(rrp)
    T["non_approved_review_receipt_rejected"]=rejected(lambda:evaluate_manifest(mm))
    # Tamper primary records.
    for base,sub,filep,prefix,name in [(rs,"prepare_review_receipts",rp,"trs","review_receipt_tamper_rejected"),(ps,"selection_transition_prepares",cp,"tps","changeset_tamper_rejected"),(ds,"selection_lifecycle_decisions",dp,"tds","decision_tamper_rejected")]:
        root=td/prefix;shutil.copytree(base,root);p=root/sub/filep.name;obj=load(p);obj["status"]="TAMPERED";w(p,obj);mm=copy.deepcopy(m)
        if name.startswith("review"):mm["review_store_root"]=str(root.resolve());mm["review_receipt_path"]=str(p.resolve());mm["review_receipt_sha256"]=sha256_file(p)
        elif name.startswith("changeset"):mm["prepare_store_root"]=str(root.resolve());mm["changeset_path"]=str(p.resolve());mm["changeset_sha256"]=sha256_file(p)
        else:mm["decision_store_root"]=str(root.resolve());mm["decision_record_path"]=str(p.resolve());mm["decision_record_sha256"]=sha256_file(p)
        T[name]=rejected(lambda mm=mm:evaluate_manifest(mm))

    # Same ceremony ID with distinct valid auth ID/content conflicts immutably.
    a2=copy.deepcopy(a);a2["authorization_id"]="A2";a2["authorizer_reference"]="synthetic-user-2";a2p=td/"a2.json";w(a2p,a2);mm=copy.deepcopy(m);mm["authorization_path"]=str(a2p.resolve());mm["authorization_sha256"]=sha256_file(a2p);m2p=td/"m2.json";w(m2p,mm)
    T["same_ceremony_id_different_content_rejected"]=rejected(lambda:process(m2p,cs))
    T["repo_internal_manifest_rejected"]=rejected(lambda:process(ROOT/"config/jnu_private_selection_transition_prepare_review_checkpoint_v1.json",cs))
    T["repo_internal_ceremony_store_rejected"]=rejected(lambda:process(mp,ROOT/"ceremony-store-forbidden"))

after={p:sha256_file(p) for p in [SHORTLIST,KEY_CURRENT,TERMS_CURRENT]};T["production_state_files_byte_identical"]=before==after
short2=load(SHORTLIST);key=load(KEY_CURRENT);terms=load(TERMS_CURRENT);mem=load(MEMORY)
T["shortlist_still_unselected"]=short2["selected_market_data_provider"]=="UNSELECTED" and short2["selected_key_custody_provider"]=="UNSELECTED"
T["production_key_still_disabled_unselected"]=key["production_enabled"] is False and key["vendor"]=="UNSELECTED" and key["region"]=="UNSELECTED"
T["provider_terms_boundary_unchanged"]=terms["broker_auth_used"] is False and terms["trading_permission_used"] is False and terms["public_output_requested"] is False
T["public_real_ledger_still_zero_zero"]=mem.get("real_live_shadow_forecasts_registered")==0 and mem.get("real_live_shadow_outcomes_registered")==0
status="PASS" if all(T.values()) else "FAIL"
print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T)},indent=2));raise SystemExit(0 if status=="PASS" else 1)
