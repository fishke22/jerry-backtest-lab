from __future__ import annotations
import copy, hashlib, json, tempfile
from pathlib import Path
from review_jnu_private_composite_evidence_dual_control_v1 import ROOT, process, evaluate_manifest, load, canonical_sha256, sha256_file

MEMORY=ROOT/"config"/"jnu_operational_framework_cross_session_memory_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"

def w(p:Path,x): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+"\n",encoding="utf-8")
def rejected(fn)->bool:
    try: fn();return False
    except Exception:return True

short=load(SHORTLIST);T={}
with tempfile.TemporaryDirectory(prefix="jnu-dual-review-") as td0:
    td=Path(td0);store=td/"store";store.mkdir()
    combos=[]
    for p in short["market_data_candidates"]:
        for k in short["key_custody_candidates"]:
            cid=p["id"]+"__"+k["id"]
            combos.append({
              "combination_id":cid,"market_data_candidate_id":p["id"],"kms_candidate_id":k["id"],
              "status":"SYNTHETIC_PREACTIVATION_EVIDENCE_COMPLETE_NOT_ACTIVATABLE","synthetic_evidence_complete":True,
              "provider_term_blockers":[],"kms_control_blockers":[],
              "activation_blockers":["SYNTHETIC_ONLY_EVIDENCE","MARKET_DATA_PROVIDER_NOT_SELECTED","KMS_PROVIDER_NOT_SELECTED","PRODUCTION_KEY_PROFILE_DISABLED","REAL_CREDENTIALS_NOT_CONNECTED","REAL_ACTIVATION_MANIFEST_NOT_GENERATED"],
              "lineage":{"provider_attestation_sha256":hashlib.sha256(("p-"+p["id"]).encode()).hexdigest(),"provider_pack_id":"P_"+p["id"],"provider_evidence_rows":3,"kms_attestation_sha256":hashlib.sha256(("k-"+k["id"]).encode()).hexdigest(),"kms_pack_id":"K_"+k["id"],"kms_evidence_rows":2},
              "rank":None,"recommended":False,"selected":False,"real_activation_authorized":False
            })
    composite={
      "version":"1.0","artifact_class":"JNU_PRIVATE_COMPOSITE_PREACTIVATION_READINESS_DOSSIERS","storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,"mode":"SYNTHETIC","join_id":"JNU_JOIN_SYNTH_REVIEW","evidence_as_of":"2026-09-08",
      "combination_count":6,"dossiers":combos,"ranking_generated":False,"recommendation_generated":False,"selection_generated":False,
      "market_data_provider_selected":False,"kms_provider_selected":False,"production_key_profile_enabled":False,"real_provider_term_current_ready":False,
      "credentials_connected":False,"real_activation_manifest_generated":False,"real_activation_authorized":False
    }
    cp=td/"composite.json";w(cp,composite)
    reviews=[]
    for i,d in enumerate(combos):
        dsha=canonical_sha256(d)
        for role,suffix in [("EVIDENCE_REVIEWER","E"),("CONTROL_REVIEWER","C")]:
            reviews.append({
              "review_id":f"R{i}_{suffix}","combination_id":d["combination_id"],"reviewer_role":role,"reviewer_id":f"synthetic-reviewer-{i}-{suffix}",
              "disposition":"APPROVE","dossier_sha256":dsha,"reviewed_at_utc":"2026-09-08T01:00:00+00:00",
              "revalidation_due_at_utc":"2026-09-15T01:00:00+00:00","expires_at_utc":"2026-09-22T01:00:00+00:00",
              "reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"
            })
    manifest={
      "version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,"review_batch_id":"JNU_REVIEW_SYNTH_001",
      "evaluation_at_utc":"2026-09-08T02:00:00+00:00","composite_dossier_path":str(cp.resolve()),
      "composite_dossier_sha256":sha256_file(cp),"reviews":reviews
    }
    mp=td/"manifest.json";w(mp,manifest)
    r1=process(mp,store);receipt_path=store/"review_receipts"/"JNU_REVIEW_SYNTH_001.json";receipt=load(receipt_path);raw=receipt_path.read_text(encoding="utf-8")
    T["baseline_receipt_written"]=r1["status"]=="DUAL_CONTROL_RECEIPT_WRITTEN"
    T["six_combinations_reviewed"]=receipt["combination_count"]==6 and len(receipt["results"])==6
    T["twelve_reviews_required"]=receipt["review_count"]==12
    T["all_approved_not_activatable"]=all(x["outcome"]=="SYNTHETIC_DUAL_CONTROL_APPROVED_NOT_ACTIVATABLE" and x["real_activation_authorized"] is False for x in receipt["results"])
    T["no_selection_or_ranking"]=receipt["selection_generated"] is False and receipt["ranking_generated"] is False and receipt["recommendation_generated"] is False
    T["reviewer_ids_redacted"]=receipt["reviewer_ids_emitted"] is False and "synthetic-reviewer-" not in raw and all(len(r["reviewer_ref_sha256"])==64 for x in receipt["results"] for r in x["reviews"])
    T["activation_blockers_retained"]=all("SYNTHETIC_ONLY_REVIEW" in x["activation_blockers"] and "MARKET_DATA_PROVIDER_NOT_SELECTED" in x["activation_blockers"] for x in receipt["results"])
    r2=process(mp,store)
    T["exact_replay_idempotent"]=r2["status"]=="IDEMPOTENT_REPLAY_ACCEPTED" and r2["receipt_sha256"]==r1["receipt_sha256"]

    changed=copy.deepcopy(manifest);changed["reviews"][0]["disposition"]="REJECT";cmp=td/"changed-same-batch.json";w(cmp,changed)
    T["same_batch_different_receipt_rejected"]=rejected(lambda:process(cmp,store))

    bad=copy.deepcopy(manifest);bad["mode"]="REAL";bad["synthetic_fixture"]=False
    T["real_mode_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["composite_dossier_sha256"]="0"*64
    T["wrong_composite_hash_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["reviews"][0]["dossier_sha256"]="0"*64
    T["wrong_dossier_hash_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["reviews"][1]["review_id"]=bad["reviews"][0]["review_id"]
    T["duplicate_review_id_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["reviews"][1]["reviewer_id"]=bad["reviews"][0]["reviewer_id"]
    T["same_reviewer_dual_role_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["reviews"]=bad["reviews"][:-1]
    T["missing_review_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["reviews"][0]["reviewer_role"]="UNKNOWN_ROLE"
    T["invalid_role_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["reviews"][0]["disposition"]="MAYBE"
    T["invalid_disposition_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["reviews"][0]["reviewer_attestation"]="INFERRED"
    T["inferred_review_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["reviews"][0]["reviewed_at_utc"]="2026-09-08T01:00:00"
    T["naive_review_time_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["reviews"][0]["revalidation_due_at_utc"]="2026-09-08T00:00:00+00:00"
    T["revalidation_before_review_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["reviews"][0]["expires_at_utc"]="2026-09-10T00:00:00+00:00";bad["reviews"][0]["revalidation_due_at_utc"]="2026-09-11T00:00:00+00:00"
    T["expiry_before_revalidation_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["evaluation_at_utc"]="2026-09-08T00:30:00+00:00"
    T["evaluation_before_review_rejected"]=rejected(lambda:evaluate_manifest(bad))

    stale=copy.deepcopy(manifest);stale["review_batch_id"]="JNU_REVIEW_SYNTH_STALE";stale["evaluation_at_utc"]="2026-09-16T02:00:00+00:00"
    so=evaluate_manifest(stale)
    T["revalidation_due_blocks_all"]=all(x["outcome"]=="SYNTHETIC_DUAL_CONTROL_REVALIDATION_REQUIRED" for x in so["results"])
    expired=copy.deepcopy(manifest);expired["review_batch_id"]="JNU_REVIEW_SYNTH_EXPIRED";expired["evaluation_at_utc"]="2026-09-23T02:00:00+00:00"
    eo=evaluate_manifest(expired)
    T["expired_blocks_all"]=all(x["outcome"]=="SYNTHETIC_DUAL_CONTROL_REVALIDATION_REQUIRED" for x in eo["results"])

    conflict=copy.deepcopy(manifest);conflict["review_batch_id"]="JNU_REVIEW_SYNTH_CONFLICT";conflict["reviews"][0]["disposition"]="REJECT"
    co=evaluate_manifest(conflict);target=manifest["reviews"][0]["combination_id"]
    T["disposition_conflict_blocks_exact_one"]=sum(x["outcome"]=="SYNTHETIC_DUAL_CONTROL_CONFLICT_BLOCKED" for x in co["results"])==1 and next(x for x in co["results"] if x["combination_id"]==target)["outcome"]=="SYNTHETIC_DUAL_CONTROL_CONFLICT_BLOCKED"
    bothreject=copy.deepcopy(manifest);bothreject["review_batch_id"]="JNU_REVIEW_SYNTH_REJECT";bothreject["reviews"][0]["disposition"]="REJECT";bothreject["reviews"][1]["disposition"]="REJECT"
    bro=evaluate_manifest(bothreject)
    T["dual_reject_is_rejected"]=next(x for x in bro["results"] if x["combination_id"]==target)["outcome"]=="SYNTHETIC_DUAL_CONTROL_REJECTED"
    needs=copy.deepcopy(manifest);needs["review_batch_id"]="JNU_REVIEW_SYNTH_NEEDS";needs["reviews"][0]["disposition"]="NEEDS_EVIDENCE";needs["reviews"][1]["disposition"]="NEEDS_EVIDENCE"
    no=evaluate_manifest(needs)
    T["dual_needs_is_needs_evidence"]=next(x for x in no["results"] if x["combination_id"]==target)["outcome"]=="SYNTHETIC_DUAL_CONTROL_NEEDS_EVIDENCE"

    blocked=copy.deepcopy(composite);blocked["dossiers"][0]["synthetic_evidence_complete"]=False;blocked["dossiers"][0]["status"]="SYNTHETIC_PREACTIVATION_EVIDENCE_BLOCKED";bcp=td/"blocked-composite.json";w(bcp,blocked)
    bm=copy.deepcopy(manifest);bm["review_batch_id"]="JNU_REVIEW_SYNTH_UNDERLYING";bm["composite_dossier_path"]=str(bcp.resolve());bm["composite_dossier_sha256"]=sha256_file(bcp)
    for r in bm["reviews"]:
        d=next(d for d in blocked["dossiers"] if d["combination_id"]==r["combination_id"]);r["dossier_sha256"]=canonical_sha256(d)
    bo=evaluate_manifest(bm)
    T["underlying_block_overrides_dual_approve"]=next(x for x in bo["results"] if x["combination_id"]==blocked["dossiers"][0]["combination_id"])["outcome"]=="SYNTHETIC_DUAL_CONTROL_NEEDS_EVIDENCE"

    bad=copy.deepcopy(manifest);bad["api_key"]="x"
    T["secret_field_in_manifest_rejected"]=rejected(lambda:evaluate_manifest(bad))
    secretcomp=copy.deepcopy(composite);secretcomp["key_id"]="x";scp=td/"secret-composite.json";w(scp,secretcomp)
    bad=copy.deepcopy(manifest);bad["composite_dossier_path"]=str(scp.resolve());bad["composite_dossier_sha256"]=sha256_file(scp)
    T["cloud_key_identifier_in_composite_rejected"]=rejected(lambda:evaluate_manifest(bad))
    ranked=copy.deepcopy(composite);ranked["ranking_generated"]=True;rcp=td/"ranked-composite.json";w(rcp,ranked)
    bad=copy.deepcopy(manifest);bad["composite_dossier_path"]=str(rcp.resolve());bad["composite_dossier_sha256"]=sha256_file(rcp)
    T["ranked_composite_rejected"]=rejected(lambda:evaluate_manifest(bad))
    selected=copy.deepcopy(composite);selected["dossiers"][0]["selected"]=True;scp2=td/"selected-composite.json";w(scp2,selected)
    bad=copy.deepcopy(manifest);bad["composite_dossier_path"]=str(scp2.resolve());bad["composite_dossier_sha256"]=sha256_file(scp2)
    T["selected_dossier_rejected"]=rejected(lambda:evaluate_manifest(bad))
    activated=copy.deepcopy(composite);activated["real_activation_authorized"]=True;acp=td/"activated-composite.json";w(acp,activated)
    bad=copy.deepcopy(manifest);bad["composite_dossier_path"]=str(acp.resolve());bad["composite_dossier_sha256"]=sha256_file(acp)
    T["activation_authorized_composite_rejected"]=rejected(lambda:evaluate_manifest(bad))
    badcomp=copy.deepcopy(composite);badcomp["dossiers"]=badcomp["dossiers"][:-1];badcomp["combination_count"]=5;bcp2=td/"missing-combo.json";w(bcp2,badcomp)
    bad=copy.deepcopy(manifest);bad["composite_dossier_path"]=str(bcp2.resolve());bad["composite_dossier_sha256"]=sha256_file(bcp2)
    T["missing_combination_rejected"]=rejected(lambda:evaluate_manifest(bad))
    dupcomp=copy.deepcopy(composite);dupcomp["dossiers"][-1]=copy.deepcopy(dupcomp["dossiers"][0]);dcp=td/"dup-combo.json";w(dcp,dupcomp)
    bad=copy.deepcopy(manifest);bad["composite_dossier_path"]=str(dcp.resolve());bad["composite_dossier_sha256"]=sha256_file(dcp)
    T["duplicate_combination_rejected"]=rejected(lambda:evaluate_manifest(bad))
    T["repo_internal_manifest_rejected"]=rejected(lambda:process(ROOT/"config/jnu_private_composite_production_readiness_checkpoint_v1.json",store))
    T["repo_internal_review_store_rejected"]=rejected(lambda:process(mp,ROOT/"review-store-forbidden"))

mem=load(MEMORY);key=load(KEY_CURRENT);terms=load(TERMS_CURRENT);short2=load(SHORTLIST)
T["public_real_ledger_still_zero_zero"]=mem.get("real_live_shadow_forecasts_registered")==0 and mem.get("real_live_shadow_outcomes_registered")==0
T["shortlist_still_unselected"]=short2.get("selected_market_data_provider")=="UNSELECTED" and short2.get("selected_key_custody_provider")=="UNSELECTED"
T["production_key_still_disabled"]=key.get("production_enabled") is False and key.get("vendor")=="UNSELECTED" and key.get("region")=="UNSELECTED"
T["real_provider_terms_still_unresolved"]=any(v=="UNRESOLVED" for k,v in terms.items() if k.endswith("_status"))
status="PASS" if all(T.values()) else "FAIL"
print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T)},indent=2))
raise SystemExit(0 if status=="PASS" else 1)
