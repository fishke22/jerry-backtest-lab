from __future__ import annotations
import copy, hashlib, json, shutil, tempfile
from pathlib import Path
from review_jnu_private_selection_transition_prepare_v1 import ROOT, process, evaluate_manifest, load, sha256_file
from jnu_private_atomic_io_v1 import write_immutable_json

SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"
MEMORY=ROOT/"config"/"jnu_operational_framework_cross_session_memory_v1.json"

def w(p:Path,x): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+"\n",encoding="utf-8")
def rejected(fn)->bool:
    try: fn();return False
    except Exception:return True

short=load(SHORTLIST);pairs=[p["id"]+"__"+k["id"] for p in short["market_data_candidates"] for k in short["key_custody_candidates"]];T={}
before={p:sha256_file(p) for p in [SHORTLIST,KEY_CURRENT,TERMS_CURRENT]}
with tempfile.TemporaryDirectory(prefix="jnu-prepare-review-") as td0:
    td=Path(td0);ds=td/"decision-store";ds.mkdir();ps=td/"prepare-store";ps.mkdir();rs=td/"review-store";rs.mkdir()
    pair=pairs[0];pid,kid=pair.split("__",1)
    decision={
      "version":"1.0","artifact_class":"JNU_SYNTHETIC_SELECTION_DECISION_LIFECYCLE_CURRENT_AUTH_RECORD","storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,"mode":"SYNTHETIC","status":"SYNTHETIC_LIFECYCLE_CURRENT_AUTH_VALIDATED_NO_SELECTION",
      "decision_id":"JNU_SELECTION_DECISION_SYNTH_REVIEW_SOURCE","decision_at_utc":"2026-09-08T09:00:00+00:00",
      "requested_combination_id":pair,"requested_market_data_candidate_id":pid,"requested_kms_candidate_id":kid,
      "review_batch_id":"UPSTREAM","review_receipt_sha256":hashlib.sha256(b"r").hexdigest(),"composite_dossier_sha256":hashlib.sha256(b"c").hexdigest(),
      "authorization_id":"A","authorization_sha256":hashlib.sha256(b"a").hexdigest(),"authorizer_ref_sha256":hashlib.sha256(b"ar").hexdigest(),
      "authorization_status":"SYNTHETIC_DISABLED","base_authorization_binding_validated":True,"dual_control_approval_validated":True,
      "exact_six_pair_coverage_validated":True,"lifecycle_full_chain_validated":True,"lifecycle_event_backups_validated":True,
      "lifecycle_current_authorization_validated":True,"lifecycle_event_count":3,"lifecycle_head_sha256":hashlib.sha256(b"head").hexdigest(),
      "lifecycle_current_status":"ACTIVE","selected_market_data_provider":"UNSELECTED","selected_key_custody_provider":"UNSELECTED",
      "selected_combination_id":"UNSELECTED","selection_transition_permitted":False,"selection_written":False,"production_state_mutated":False,
      "credentials_connected":False,"kms_api_called":False,"key_created":False,"real_activation_manifest_generated":False,"real_activation_authorized":False
    }
    dp=ds/"selection_lifecycle_decisions"/"decision.json";write_immutable_json(ds,dp,decision)
    snaps={
      "PROVIDER_SELECTION_SHORTLIST":{"path":"config/jnu_provider_selection_shortlist_v1.json","sha256":sha256_file(SHORTLIST)},
      "PRODUCTION_KEY_CUSTODY_CURRENT":{"path":"config/jnu_production_key_custody_current_v1.json","sha256":sha256_file(KEY_CURRENT)},
      "PROVIDER_TERM_READINESS_CURRENT":{"path":"config/jnu_provider_term_readiness_current_v1.json","sha256":sha256_file(TERMS_CURRENT)}
    }
    changeset={
      "version":"1.0","artifact_class":"JNU_SYNTHETIC_SELECTION_TRANSITION_PREPARE_CHANGESET","storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,"mode":"SYNTHETIC","status":"SYNTHETIC_PREPARE_ONLY_CHANGESET_READY_NOT_COMMITTABLE",
      "prepare_id":"JNU_SELECTION_PREPARE_SYNTH_REVIEW","prepared_at_utc":"2026-09-08T09:10:00+00:00","operation":"PREPARE_ONLY",
      "request_binding_sha256":hashlib.sha256(b"req").hexdigest(),"decision_id":decision["decision_id"],"decision_record_sha256":sha256_file(dp),
      "lifecycle_event_count":3,"lifecycle_head_sha256":decision["lifecycle_head_sha256"],"requested_combination_id":pair,
      "requested_market_data_candidate_id":pid,"requested_kms_candidate_id":kid,"production_state_preconditions":snaps,
      "compare_and_swap_required":True,"intended_mutations_preview":[],"rollback_recovery":{"preimage_sha256_bound":True},
      "commit_capability":False,"apply_capability":False,"selection_transition_permitted":False,"selection_written":False,
      "selected_market_data_provider":"UNSELECTED","selected_key_custody_provider":"UNSELECTED","selected_combination_id":"UNSELECTED",
      "production_state_mutated":False,"credentials_connected":False,"kms_api_called":False,"key_created":False,
      "real_activation_manifest_generated":False,"real_activation_authorized":False
    }
    cp=ps/"selection_transition_prepares"/"prepare.json";write_immutable_json(ps,cp,changeset)
    def reviews(d1="APPROVE",d2="APPROVE",r2id="reviewer-control",reval="2026-09-10T10:00:00+00:00",expiry="2026-09-11T10:00:00+00:00"):
        base={"changeset_sha256":sha256_file(cp),"decision_record_sha256":sha256_file(dp),"requested_combination_id":pair,
              "reviewed_at_utc":"2026-09-08T10:00:00+00:00","revalidation_due_at_utc":reval,"expires_at_utc":expiry,"reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"}
        a={**base,"review_id":"REV_CHANGE","reviewer_role":"CHANGE_REVIEWER","reviewer_id":"reviewer-change","disposition":d1}
        b={**base,"review_id":"REV_CONTROL","reviewer_role":"CONTROL_REVIEWER","reviewer_id":r2id,"disposition":d2}
        return [a,b]
    manifest={
      "version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,"review_batch_id":"JNU_PREPARE_REVIEW_SYNTH_001",
      "evaluation_at_utc":"2026-09-08T11:00:00+00:00",
      "prepare_store_root":str(ps.resolve()),"changeset_path":str(cp.resolve()),"changeset_sha256":sha256_file(cp),
      "decision_store_root":str(ds.resolve()),"decision_record_path":str(dp.resolve()),"decision_record_sha256":sha256_file(dp),
      "reviews":reviews()
    }
    mp=td/"manifest.json";w(mp,manifest);r=process(mp,rs);rp=rs/"prepare_review_receipts"/(manifest["review_batch_id"]+".json");out=load(rp);raw=rp.read_text(encoding="utf-8")
    T["baseline_review_written"]=r["status"]=="SYNTHETIC_PREPARE_DUAL_CONTROL_REVIEW_RECORDED"
    T["dual_approve_not_committable"]=out["outcome"]=="SYNTHETIC_DUAL_CONTROL_APPROVED_PREPARE_NOT_COMMITTABLE" and out["commit_capability"] is False and out["apply_capability"] is False
    T["cas_revalidated_fresh"]=out["cas_revalidated_at_review"] is True and out["cas_state_fresh"] is True
    T["two_reviews_emitted"]=out["review_count"]==2 and len(out["reviews"])==2
    T["reviewer_ids_redacted"]="reviewer-change" not in raw and "reviewer-control" not in raw and all("reviewer_ref_sha256" in x for x in out["reviews"])
    T["decision_lineage_preserved"]=out["decision_record_sha256"]==sha256_file(dp) and out["lifecycle_head_sha256"]==decision["lifecycle_head_sha256"] and out["lifecycle_event_count"]==3
    T["pair_binding_preserved"]=out["requested_combination_id"]==pair and out["requested_market_data_candidate_id"]==pid and out["requested_kms_candidate_id"]==kid
    T["selection_still_unselected"]=out["selection_written"] is False and out["selected_market_data_provider"]=="UNSELECTED" and out["selected_key_custody_provider"]=="UNSELECTED"
    T["production_activation_false"]=out["production_state_mutated"] is False and out["real_activation_authorized"] is False
    T["exact_replay_idempotent"]=process(mp,rs)["status"]=="IDEMPOTENT_REPLAY_ACCEPTED"

    x=copy.deepcopy(manifest);x["changeset_sha256"]="0"*64;T["wrong_changeset_hash_rejected"]=rejected(lambda:evaluate_manifest(x))
    x=copy.deepcopy(manifest);x["decision_record_sha256"]="0"*64;T["wrong_decision_hash_rejected"]=rejected(lambda:evaluate_manifest(x))
    x=copy.deepcopy(manifest);x["reviews"][0]["changeset_sha256"]="0"*64;T["review_changeset_binding_rejected"]=rejected(lambda:evaluate_manifest(x))
    x=copy.deepcopy(manifest);x["reviews"][0]["decision_record_sha256"]="0"*64;T["review_decision_binding_rejected"]=rejected(lambda:evaluate_manifest(x))
    x=copy.deepcopy(manifest);x["reviews"][0]["requested_combination_id"]=pairs[1];T["pair_substitution_rejected"]=rejected(lambda:evaluate_manifest(x))
    x=copy.deepcopy(manifest);x["reviews"]=x["reviews"][:1];T["missing_review_rejected"]=rejected(lambda:evaluate_manifest(x))
    x=copy.deepcopy(manifest);x["reviews"][1]["reviewer_role"]="CHANGE_REVIEWER";T["duplicate_role_rejected"]=rejected(lambda:evaluate_manifest(x))
    x=copy.deepcopy(manifest);x["reviews"][1]["reviewer_id"]="reviewer-change";T["same_reviewer_dual_role_rejected"]=rejected(lambda:evaluate_manifest(x))
    x=copy.deepcopy(manifest);x["reviews"][1]["review_id"]="REV_CHANGE";T["duplicate_review_id_rejected"]=rejected(lambda:evaluate_manifest(x))
    x=copy.deepcopy(manifest);x["reviews"][0]["disposition"]="MAYBE";T["invalid_disposition_rejected"]=rejected(lambda:evaluate_manifest(x))
    x=copy.deepcopy(manifest);x["reviews"][0]["reviewer_attestation"]="INFERRED";T["inferred_review_rejected"]=rejected(lambda:evaluate_manifest(x))
    x=copy.deepcopy(manifest);x["reviews"][0]["reviewed_at_utc"]="2026-09-08T10:00:00";T["naive_review_time_rejected"]=rejected(lambda:evaluate_manifest(x))
    x=copy.deepcopy(manifest);x["reviews"][0]["revalidation_due_at_utc"]="2026-09-08T09:00:00+00:00";T["bad_revalidation_order_rejected"]=rejected(lambda:evaluate_manifest(x))
    x=copy.deepcopy(manifest);x["reviews"][0]["expires_at_utc"]="2026-09-08T09:30:00+00:00";T["bad_expiry_order_rejected"]=rejected(lambda:evaluate_manifest(x))
    x=copy.deepcopy(manifest);x["evaluation_at_utc"]="2026-09-08T09:00:00+00:00";T["evaluation_before_review_rejected"]=rejected(lambda:evaluate_manifest(x))

    x=copy.deepcopy(manifest);x["evaluation_at_utc"]="2026-09-10T10:00:00+00:00";o=evaluate_manifest(x)
    T["revalidation_due_blocks"]=o["outcome"]=="SYNTHETIC_DUAL_CONTROL_REVALIDATION_REQUIRED_PREPARE"
    x=copy.deepcopy(manifest);x["evaluation_at_utc"]="2026-09-12T00:00:00+00:00";o=evaluate_manifest(x)
    T["expiry_blocks"]=o["outcome"]=="SYNTHETIC_DUAL_CONTROL_REVALIDATION_REQUIRED_PREPARE"
    x=copy.deepcopy(manifest);x["reviews"]=reviews("APPROVE","REJECT");o=evaluate_manifest(x)
    T["disposition_conflict_blocks"]=o["outcome"]=="SYNTHETIC_DUAL_CONTROL_CONFLICT_BLOCKED_PREPARE"
    x=copy.deepcopy(manifest);x["reviews"]=reviews("REJECT","REJECT");o=evaluate_manifest(x)
    T["dual_reject_status"]=o["outcome"]=="SYNTHETIC_DUAL_CONTROL_REJECTED_PREPARE"
    x=copy.deepcopy(manifest);x["reviews"]=reviews("NEEDS_EVIDENCE","NEEDS_EVIDENCE");o=evaluate_manifest(x)
    T["dual_needs_evidence_status"]=o["outcome"]=="SYNTHETIC_DUAL_CONTROL_NEEDS_EVIDENCE_PREPARE"

    # Semantically committable/apply-capable changesets are rejected even with valid immutable backup.
    ps2=td/"ps2";ps2.mkdir();bad=copy.deepcopy(changeset);bad["commit_capability"]=True;bp=ps2/"selection_transition_prepares"/"bad.json";write_immutable_json(ps2,bp,bad)
    x=copy.deepcopy(manifest);x["prepare_store_root"]=str(ps2.resolve());x["changeset_path"]=str(bp.resolve());x["changeset_sha256"]=sha256_file(bp);x["reviews"]=reviews()
    for q in x["reviews"]:q["changeset_sha256"]=sha256_file(bp)
    T["commit_capable_changeset_rejected"]=rejected(lambda:evaluate_manifest(x))
    ps3=td/"ps3";ps3.mkdir();bad2=copy.deepcopy(changeset);bad2["apply_capability"]=True;bp2=ps3/"selection_transition_prepares"/"bad2.json";write_immutable_json(ps3,bp2,bad2)
    x=copy.deepcopy(manifest);x["prepare_store_root"]=str(ps3.resolve());x["changeset_path"]=str(bp2.resolve());x["changeset_sha256"]=sha256_file(bp2);x["reviews"]=reviews()
    for q in x["reviews"]:q["changeset_sha256"]=sha256_file(bp2)
    T["apply_capable_changeset_rejected"]=rejected(lambda:evaluate_manifest(x))

    # Tamper primary changeset and decision.
    tamps=td/"tamps";shutil.copytree(ps,tamps);tcp=tamps/"selection_transition_prepares"/cp.name;tx=load(tcp);tx["status"]="TAMPERED";w(tcp,tx)
    x=copy.deepcopy(manifest);x["prepare_store_root"]=str(tamps.resolve());x["changeset_path"]=str(tcp.resolve());x["changeset_sha256"]=sha256_file(tcp)
    for q in x["reviews"]:q["changeset_sha256"]=sha256_file(tcp)
    T["changeset_backup_tamper_rejected"]=rejected(lambda:evaluate_manifest(x))
    tamds=td/"tamds";shutil.copytree(ds,tamds);tdp=tamds/"selection_lifecycle_decisions"/dp.name;dx=load(tdp);dx["status"]="TAMPERED";w(tdp,dx)
    x=copy.deepcopy(manifest);x["decision_store_root"]=str(tamds.resolve());x["decision_record_path"]=str(tdp.resolve());x["decision_record_sha256"]=sha256_file(tdp)
    for q in x["reviews"]:q["decision_record_sha256"]=sha256_file(tdp)
    T["decision_backup_tamper_rejected"]=rejected(lambda:evaluate_manifest(x))

    # CAS stale-state output is blocked, without editing actual repo files: use a changeset with a stale but well-formed expected hash.
    ps4=td/"ps4";ps4.mkdir();stale=copy.deepcopy(changeset);stale["production_state_preconditions"]["PROVIDER_SELECTION_SHORTLIST"]["sha256"]="0"*64;sp=ps4/"selection_transition_prepares"/"stale.json";write_immutable_json(ps4,sp,stale)
    x=copy.deepcopy(manifest);x["prepare_store_root"]=str(ps4.resolve());x["changeset_path"]=str(sp.resolve());x["changeset_sha256"]=sha256_file(sp);x["reviews"]=reviews()
    for q in x["reviews"]:q["changeset_sha256"]=sha256_file(sp)
    o=evaluate_manifest(x);T["stale_cas_state_blocks_approval"]=o["outcome"]=="SYNTHETIC_DUAL_CONTROL_STALE_STATE_BLOCKED_PREPARE" and o["cas_state_fresh"] is False

    x=copy.deepcopy(manifest);x["api_key"]="x";T["secret_field_rejected"]=rejected(lambda:evaluate_manifest(x))
    x=copy.deepcopy(manifest);x["mode"]="REAL";T["real_mode_rejected"]=rejected(lambda:evaluate_manifest(x))

    # Same batch id, different otherwise valid review content conflicts immutably.
    x=copy.deepcopy(manifest);x["reviews"]=reviews("REJECT","REJECT");xp=td/"collision.json";w(xp,x)
    T["same_batch_id_different_content_rejected"]=rejected(lambda:process(xp,rs))

    T["repo_internal_manifest_rejected"]=rejected(lambda:process(ROOT/"config/jnu_private_selection_transition_prepare_checkpoint_v1.json",rs))
    T["repo_internal_prepare_store_rejected"]=rejected(lambda:evaluate_manifest({**manifest,"prepare_store_root":str(ROOT)}))
    T["repo_internal_decision_store_rejected"]=rejected(lambda:evaluate_manifest({**manifest,"decision_store_root":str(ROOT)}))
    T["repo_internal_review_store_rejected"]=rejected(lambda:process(mp,ROOT/"prepare-review-store-forbidden"))

after={p:sha256_file(p) for p in [SHORTLIST,KEY_CURRENT,TERMS_CURRENT]}
T["production_state_files_byte_identical"]=before==after
short2=load(SHORTLIST);key=load(KEY_CURRENT);terms=load(TERMS_CURRENT);mem=load(MEMORY)
T["shortlist_still_unselected"]=short2["selected_market_data_provider"]=="UNSELECTED" and short2["selected_key_custody_provider"]=="UNSELECTED"
T["production_key_still_disabled_unselected"]=key["production_enabled"] is False and key["vendor"]=="UNSELECTED" and key["region"]=="UNSELECTED"
T["provider_terms_boundary_unchanged"]=terms["broker_auth_used"] is False and terms["trading_permission_used"] is False and terms["public_output_requested"] is False
T["public_real_ledger_still_zero_zero"]=mem.get("real_live_shadow_forecasts_registered")==0 and mem.get("real_live_shadow_outcomes_registered")==0
status="PASS" if all(T.values()) else "FAIL"
print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T)},indent=2))
raise SystemExit(0 if status=="PASS" else 1)
