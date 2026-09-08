from __future__ import annotations
import copy, hashlib, json, shutil, tempfile
from pathlib import Path
from prepare_jnu_private_selection_transition_changeset_v1 import ROOT, process, evaluate_request, load, sha256_file
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
with tempfile.TemporaryDirectory(prefix="jnu-selection-prepare-") as td0:
    td=Path(td0);decision_store=td/"decision-store";decision_store.mkdir();prepare_store=td/"prepare-store";prepare_store.mkdir()
    pair=pairs[0];provider_id,kms_id=pair.split("__",1)
    decision={
      "version":"1.0","artifact_class":"JNU_SYNTHETIC_SELECTION_DECISION_LIFECYCLE_CURRENT_AUTH_RECORD","storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,"mode":"SYNTHETIC","status":"SYNTHETIC_LIFECYCLE_CURRENT_AUTH_VALIDATED_NO_SELECTION",
      "decision_id":"JNU_SELECTION_DECISION_SYNTH_PREPARE_SOURCE","decision_at_utc":"2026-09-08T08:00:00+00:00",
      "requested_combination_id":pair,"requested_market_data_candidate_id":provider_id,"requested_kms_candidate_id":kms_id,
      "review_batch_id":"JNU_REVIEW_SYNTH_PREPARE","review_receipt_sha256":hashlib.sha256(b"receipt").hexdigest(),
      "composite_dossier_sha256":hashlib.sha256(b"composite").hexdigest(),"authorization_id":"JNU_AUTH_SYNTH_PREPARE",
      "authorization_sha256":hashlib.sha256(b"auth").hexdigest(),"authorizer_ref_sha256":hashlib.sha256(b"authorizer").hexdigest(),
      "authorization_status":"SYNTHETIC_DISABLED","base_authorization_binding_validated":True,"dual_control_approval_validated":True,
      "exact_six_pair_coverage_validated":True,"lifecycle_full_chain_validated":True,"lifecycle_event_backups_validated":True,
      "lifecycle_current_authorization_validated":True,"lifecycle_event_count":3,"lifecycle_head_sha256":hashlib.sha256(b"lifehead").hexdigest(),
      "lifecycle_current_status":"ACTIVE","selected_market_data_provider":"UNSELECTED","selected_key_custody_provider":"UNSELECTED",
      "selected_combination_id":"UNSELECTED","selection_transition_permitted":False,"selection_written":False,"production_state_mutated":False,
      "credentials_connected":False,"kms_api_called":False,"key_created":False,"real_activation_manifest_generated":False,"real_activation_authorized":False
    }
    dp=decision_store/"selection_lifecycle_decisions"/(decision["decision_id"]+".json")
    write_immutable_json(decision_store,dp,decision)
    req={
      "version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,"operation":"PREPARE_ONLY",
      "prepare_id":"JNU_SELECTION_PREPARE_SYNTH_001","prepared_at_utc":"2026-09-08T08:10:00+00:00",
      "decision_store_root":str(decision_store.resolve()),"decision_record_path":str(dp.resolve()),"decision_record_sha256":sha256_file(dp),
      "requested_combination_id":pair,"lifecycle_expected_event_count":3,"lifecycle_expected_head_sha256":decision["lifecycle_head_sha256"],
      "production_state_sha256":{
        "PROVIDER_SELECTION_SHORTLIST":sha256_file(SHORTLIST),
        "PRODUCTION_KEY_CUSTODY_CURRENT":sha256_file(KEY_CURRENT),
        "PROVIDER_TERM_READINESS_CURRENT":sha256_file(TERMS_CURRENT)
      }
    }
    qp=td/"prepare.json";w(qp,req);r1=process(qp,prepare_store)
    cp=prepare_store/"selection_transition_prepares"/(req["prepare_id"]+".json");out=load(cp);raw=cp.read_text(encoding="utf-8")
    T["baseline_prepare_written"]=r1["status"]=="SYNTHETIC_PREPARE_CHANGESET_WRITTEN"
    T["commit_capability_false"]=out["commit_capability"] is False
    T["apply_capability_false"]=out["apply_capability"] is False
    T["selection_not_written"]=out["selection_written"] is False and out["selected_combination_id"]=="UNSELECTED"
    T["production_not_mutated"]=out["production_state_mutated"] is False
    T["decision_hash_bound"]=out["decision_record_sha256"]==sha256_file(dp)
    T["lifecycle_head_count_bound"]=out["lifecycle_event_count"]==3 and out["lifecycle_head_sha256"]==decision["lifecycle_head_sha256"]
    T["exact_three_state_snapshots_bound"]=set(out["production_state_preconditions"])=={"PROVIDER_SELECTION_SHORTLIST","PRODUCTION_KEY_CUSTODY_CURRENT","PROVIDER_TERM_READINESS_CURRENT"}
    T["cas_required"]=out["compare_and_swap_required"] is True
    T["shortlist_preview_explicit"]=any(x.get("field")=="selected_market_data_provider" and x.get("preview_to")==provider_id for x in out["intended_mutations_preview"])
    T["kms_preview_keeps_production_disabled"]=any(x.get("state_id")=="PRODUCTION_KEY_CUSTODY_CURRENT" and x.get("production_enabled_preview") is False for x in out["intended_mutations_preview"])
    T["provider_terms_requires_revalidation"]=any(x.get("state_id")=="PROVIDER_TERM_READINESS_CURRENT" and x.get("apply_supported") is False for x in out["intended_mutations_preview"])
    T["rollback_metadata_present"]=out["rollback_recovery"]["future_commit_requires_private_preimage_backup"] is True and out["rollback_recovery"]["prepare_stage_created_production_backup"] is False
    T["no_decision_store_path_emitted"]=str(decision_store.resolve()) not in raw
    T["exact_replay_idempotent"]=process(qp,prepare_store)["status"]=="IDEMPOTENT_REPLAY_ACCEPTED"

    for op,name in [("COMMIT","commit_operation_rejected"),("APPLY","apply_operation_rejected"),("PREPARE_AND_COMMIT","prepare_commit_operation_rejected")]:
        x=copy.deepcopy(req);x["operation"]=op
        T[name]=rejected(lambda x=x:evaluate_request(x))
    x=copy.deepcopy(req);x["mode"]="REAL";T["real_mode_rejected"]=rejected(lambda:evaluate_request(x))
    x=copy.deepcopy(req);x["synthetic_fixture"]=False;T["non_synthetic_fixture_rejected"]=rejected(lambda:evaluate_request(x))
    x=copy.deepcopy(req);x["decision_record_sha256"]="0"*64;T["wrong_decision_hash_rejected"]=rejected(lambda:evaluate_request(x))
    x=copy.deepcopy(req);x["requested_combination_id"]=pairs[1];T["pair_mismatch_rejected"]=rejected(lambda:evaluate_request(x))
    x=copy.deepcopy(req);x["lifecycle_expected_event_count"]=4;T["lifecycle_count_mismatch_rejected"]=rejected(lambda:evaluate_request(x))
    x=copy.deepcopy(req);x["lifecycle_expected_head_sha256"]="0"*64;T["lifecycle_head_mismatch_rejected"]=rejected(lambda:evaluate_request(x))
    x=copy.deepcopy(req);del x["production_state_sha256"]["PROVIDER_TERM_READINESS_CURRENT"];T["missing_state_snapshot_rejected"]=rejected(lambda:evaluate_request(x))
    x=copy.deepcopy(req);x["production_state_sha256"]["PRODUCTION_KEY_CUSTODY_CURRENT"]="0"*64;T["stale_state_snapshot_rejected"]=rejected(lambda:evaluate_request(x))
    x=copy.deepcopy(req);x["api_key"]="x";T["secret_field_rejected"]=rejected(lambda:evaluate_request(x))

    # Decision primary tamper.
    tamstore=td/"tam-decision";shutil.copytree(decision_store,tamstore);tdp=tamstore/"selection_lifecycle_decisions"/dp.name
    tx=load(tdp);tx["status"]="TAMPERED";w(tdp,tx)
    x=copy.deepcopy(req);x["decision_store_root"]=str(tamstore.resolve());x["decision_record_path"]=str(tdp.resolve());x["decision_record_sha256"]=sha256_file(tdp)
    T["tampered_decision_backup_mismatch_rejected"]=rejected(lambda:evaluate_request(x))

    # Semantically invalid but immutably backed decision.
    badstore=td/"bad-decision";badstore.mkdir();bad=copy.deepcopy(decision);bad["selection_written"]=True
    bdp=badstore/"selection_lifecycle_decisions"/"bad.json";write_immutable_json(badstore,bdp,bad)
    x=copy.deepcopy(req);x["decision_store_root"]=str(badstore.resolve());x["decision_record_path"]=str(bdp.resolve());x["decision_record_sha256"]=sha256_file(bdp)
    T["decision_with_selection_written_rejected"]=rejected(lambda:evaluate_request(x))
    badstore2=td/"bad-decision2";badstore2.mkdir();bad2=copy.deepcopy(decision);bad2["real_activation_authorized"]=True
    bdp2=badstore2/"selection_lifecycle_decisions"/"bad2.json";write_immutable_json(badstore2,bdp2,bad2)
    x=copy.deepcopy(req);x["decision_store_root"]=str(badstore2.resolve());x["decision_record_path"]=str(bdp2.resolve());x["decision_record_sha256"]=sha256_file(bdp2)
    T["activated_decision_rejected"]=rejected(lambda:evaluate_request(x))

    # Decision path must be from canonical subdirectory.
    wrongdir=td/"wrongdir";wrongdir.mkdir();wdp=wrongdir/"decision.json";w(wdp,decision)
    x=copy.deepcopy(req);x["decision_record_path"]=str(wdp.resolve());x["decision_record_sha256"]=sha256_file(wdp)
    T["decision_outside_canonical_store_subdir_rejected"]=rejected(lambda:evaluate_request(x))

    # Same prepare ID, different valid decision must collide immutably.
    d2=copy.deepcopy(decision);d2["decision_id"]="JNU_SELECTION_DECISION_SYNTH_PREPARE_SOURCE_2"
    d2p=decision_store/"selection_lifecycle_decisions"/(d2["decision_id"]+".json");write_immutable_json(decision_store,d2p,d2)
    x=copy.deepcopy(req);x["decision_record_path"]=str(d2p.resolve());x["decision_record_sha256"]=sha256_file(d2p)
    xp=td/"collision.json";w(xp,x)
    T["same_prepare_id_different_content_rejected"]=rejected(lambda:process(xp,prepare_store))

    T["repo_internal_request_rejected"]=rejected(lambda:process(ROOT/"config/jnu_private_selection_lifecycle_integration_checkpoint_v1.json",prepare_store))
    T["repo_internal_decision_store_rejected"]=rejected(lambda:evaluate_request({**req,"decision_store_root":str(ROOT)}))
    T["repo_internal_prepare_store_rejected"]=rejected(lambda:process(qp,ROOT/"prepare-store-forbidden"))

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
