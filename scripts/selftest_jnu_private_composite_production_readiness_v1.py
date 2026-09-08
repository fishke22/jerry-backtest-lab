from __future__ import annotations
import copy, hashlib, json, tempfile
from pathlib import Path
from evaluate_jnu_private_composite_production_readiness_v1 import ROOT, run, evaluate_manifest, load

MEMORY=ROOT/"config"/"jnu_operational_framework_cross_session_memory_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"
TERM_PROTO=ROOT/"config"/"jnu_provider_term_readiness_protocol_v1.json"
KMS_PROTO=ROOT/"config"/"jnu_private_kms_deployment_evidence_staging_protocol_v1.json"

def w(p:Path,x): p.write_text(json.dumps(x,indent=2)+"\n",encoding="utf-8")
def h(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def rejected(fn)->bool:
    try: fn();return False
    except Exception:return True

term_proto=load(TERM_PROTO);kms_proto=load(KMS_PROTO);short=load(SHORTLIST)
T={}
with tempfile.TemporaryDirectory(prefix="jnu-composite-join-") as td0:
    td=Path(td0)
    ready_terms={"version":"1.0","evidence_as_of":"2026-09-08"}
    for k,v in term_proto["ready_values"].items(): ready_terms[k]=v
    ready_terms["service_facilitator_required"]=False
    ready_terms["service_facilitator_approval_status"]="NOT_REQUIRED"
    ready_terms["broker_auth_used"]=False;ready_terms["trading_permission_used"]=False;ready_terms["public_output_requested"]=False

    providers=[]
    for i,c in enumerate(short["market_data_candidates"]):
        evidence={}
        for j,k in enumerate(term_proto["ready_values"]):
            evidence[k]=[{"evidence_id":f"P{i}_{j}","authority":"OSE" if k in {"entitlement_status","applicant_eligibility_status","ose_third_party_cloud_processing_status"} else "MARKET_DATA_PROVIDER","source_class":"OSE_WRITTEN_CONFIRMATION" if k in {"entitlement_status","applicant_eligibility_status","ose_third_party_cloud_processing_status"} else "PROVIDER_WRITTEN_CONFIRMATION","source_uri":f"urn:jnu:synthetic:provider:{i}:{j}","document_sha256":hashlib.sha256(f"provider-{i}-{j}".encode()).hexdigest(),"locator":f"CLAUSE:{j}"}]
        a={"version":"1.0","artifact_class":"JNU_REDACTED_PROVIDER_TERM_ATTESTATION","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"mode":"SYNTHETIC","status":"COMPLETE_EXPLICIT_TERMS","evidence_as_of":"2026-09-08","pack_id":f"JNU_TERM_SYNTH_{c['id']}","provider_terms":dict(ready_terms),"evidence_ledger":evidence,"source_count":len(evidence),"claim_count":len(evidence),"redaction":{"source_document_paths_emitted":False,"confidential_source_text_emitted":False,"credentials_emitted":False,"inferred_permission_used":False},"real_activation_authorized":False}
        p=td/f"provider-{i}.json";w(p,a)
        providers.append({"candidate_id":c["id"],"attestation_path":str(p.resolve()),"attestation_sha256":h(p),"binding_assertion":"SYNTHETIC_EXPLICIT_CANDIDATE_BINDING","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"})

    kms=[]
    for i,c in enumerate(short["key_custody_candidates"]):
        controls={}
        for ctl,rule in kms_proto["required_controls"].items():
            if rule["type"]=="candidate_vendor": val=c["vendor"]
            elif rule["type"]=="candidate_region": val=c["proposed_region"]
            elif rule["type"]=="integer_min": val=rule["minimum"]
            else: val=rule["required_value"]
            controls[ctl]={"value":val,"evidence_ids":[f"K{i}"],"locator":"CONTROL:"+ctl,"explicitness":"EXPLICIT_TEXT","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"}
        ev={f"K{i}":{"evidence_id":f"K{i}","source_role":"DEPLOYMENT_CONTROL","source_class":"INTERNAL_DEPLOYMENT_ATTESTATION","authority":"INTERNAL_CONTROL_OWNER","source_uri":f"urn:jnu:synthetic:kms:{i}","document_sha256":hashlib.sha256(f"kms-{i}".encode()).hexdigest()}}
        a={"version":"1.0","artifact_class":"JNU_REDACTED_KMS_DEPLOYMENT_CONTROL_ATTESTATION","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"mode":"SYNTHETIC","status":"COMPLETE_SYNTHETIC_CONTROL_ATTESTATION","pack_id":f"JNU_KMS_SYNTH_{c['id']}","candidate_id":c["id"],"evidence_as_of":"2026-09-08","candidate_profile":{"control_class":c["control_class"],"vendor":c["vendor"],"region":c["proposed_region"],"candidate_selected":False,"production_enabled":False},"controls":controls,"evidence_ledger":ev,"missing_controls":[],"redaction":{"source_document_paths_emitted":False,"source_document_text_emitted":False,"cloud_resource_identifiers_emitted":False,"credentials_emitted":False,"key_material_emitted":False},"vendor_selection_performed":False,"production_profile_modified":False,"real_activation_authorized":False}
        p=td/f"kms-{i}.json";w(p,a)
        kms.append({"candidate_id":c["id"],"attestation_path":str(p.resolve()),"attestation_sha256":h(p),"reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"})

    manifest={"version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,"join_id":"JNU_JOIN_SYNTH_001","evidence_as_of":"2026-09-08","provider_attestations":providers,"kms_attestations":kms}
    mp=td/"manifest.json";op=td/"dossiers.json";w(mp,manifest);rr=run(mp,op);out=load(op)
    T["baseline_emit_pass"]=rr["status"]=="SYNTHETIC_COMPOSITE_DOSSIERS_EMITTED"
    T["exact_six_combinations"]=out["combination_count"]==6 and len(out["dossiers"])==6
    T["all_six_synthetic_evidence_complete"]=all(d["synthetic_evidence_complete"] for d in out["dossiers"])
    T["all_six_not_activatable"]=all(d["status"]=="SYNTHETIC_PREACTIVATION_EVIDENCE_COMPLETE_NOT_ACTIVATABLE" and not d["real_activation_authorized"] for d in out["dossiers"])
    T["all_six_have_invariant_blockers"]=all("SYNTHETIC_ONLY_EVIDENCE" in d["activation_blockers"] and "MARKET_DATA_PROVIDER_NOT_SELECTED" in d["activation_blockers"] and "KMS_PROVIDER_NOT_SELECTED" in d["activation_blockers"] for d in out["dossiers"])
    T["no_ranking"]=out["ranking_generated"] is False and all(d["rank"] is None for d in out["dossiers"])
    T["no_recommendation"]=out["recommendation_generated"] is False and all(d["recommended"] is False for d in out["dossiers"])
    T["no_selection"]=out["selection_generated"] is False and all(d["selected"] is False for d in out["dossiers"])
    T["lineage_hashes_retained"]=all(len(d["lineage"]["provider_attestation_sha256"])==64 and len(d["lineage"]["kms_attestation_sha256"])==64 for d in out["dossiers"])
    T["production_profile_not_enabled"]=out["production_key_profile_enabled"] is False
    T["real_current_terms_not_ready"]=out["real_provider_term_current_ready"] is False
    T["real_activation_false"]=out["real_activation_authorized"] is False

    bad=copy.deepcopy(manifest);bad["mode"]="REAL";bad["synthetic_fixture"]=False
    T["real_mode_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["provider_attestations"]=bad["provider_attestations"][:2]
    T["missing_provider_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["kms_attestations"]=bad["kms_attestations"][:1]
    T["missing_kms_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["provider_attestations"][1]["candidate_id"]=bad["provider_attestations"][0]["candidate_id"]
    T["duplicate_provider_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["kms_attestations"][1]["candidate_id"]=bad["kms_attestations"][0]["candidate_id"]
    T["duplicate_kms_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["provider_attestations"][0]["candidate_id"]="UNKNOWN_PROVIDER"
    T["unknown_provider_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["kms_attestations"][0]["candidate_id"]="UNKNOWN_KMS"
    T["unknown_kms_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["provider_attestations"][0]["attestation_sha256"]="0"*64
    T["provider_attestation_wrong_hash_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["kms_attestations"][0]["attestation_sha256"]="0"*64
    T["kms_attestation_wrong_hash_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["provider_attestations"][0]["binding_assertion"]="INFERRED"
    T["provider_binding_inferred_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["provider_attestations"][0]["reviewer_attestation"]="INFERRED"
    T["provider_binding_review_missing_rejected"]=rejected(lambda:evaluate_manifest(bad))
    bad=copy.deepcopy(manifest);bad["kms_attestations"][0]["reviewer_attestation"]="INFERRED"
    T["kms_binding_review_missing_rejected"]=rejected(lambda:evaluate_manifest(bad))

    pa=load(Path(providers[0]["attestation_path"]));pa["api_key"]="x";pp=td/"provider-secret.json";w(pp,pa)
    bad=copy.deepcopy(manifest);bad["provider_attestations"][0]["attestation_path"]=str(pp.resolve());bad["provider_attestations"][0]["attestation_sha256"]=h(pp)
    T["provider_secret_field_rejected"]=rejected(lambda:evaluate_manifest(bad))
    ka=load(Path(kms[0]["attestation_path"]));ka["key_id"]="x";kp=td/"kms-keyid.json";w(kp,ka)
    bad=copy.deepcopy(manifest);bad["kms_attestations"][0]["attestation_path"]=str(kp.resolve());bad["kms_attestations"][0]["attestation_sha256"]=h(kp)
    T["kms_resource_identifier_rejected"]=rejected(lambda:evaluate_manifest(bad))

    pa=load(Path(providers[0]["attestation_path"]));pa["provider_terms"]["exact_micro_product_status"]="UNRESOLVED";pa["status"]="PARTIAL_EXPLICIT_TERMS_BLOCKED";pp=td/"provider-partial.json";w(pp,pa)
    partial=copy.deepcopy(manifest);partial["provider_attestations"][0]["attestation_path"]=str(pp.resolve());partial["provider_attestations"][0]["attestation_sha256"]=h(pp)
    po2=evaluate_manifest(partial)
    affected=[d for d in po2["dossiers"] if d["market_data_candidate_id"]==providers[0]["candidate_id"]]
    unaffected=[d for d in po2["dossiers"] if d["market_data_candidate_id"]!=providers[0]["candidate_id"]]
    T["partial_provider_blocks_exact_two_pairs"]=len(affected)==2 and all(not d["synthetic_evidence_complete"] for d in affected) and all(d["synthetic_evidence_complete"] for d in unaffected)

    ka=load(Path(kms[0]["attestation_path"]));ka["controls"].pop("private_network_path_or_equivalent_restriction");ka["status"]="PARTIAL_SYNTHETIC_CONTROL_ATTESTATION_BLOCKED";kp=td/"kms-partial.json";w(kp,ka)
    partial=copy.deepcopy(manifest);partial["kms_attestations"][0]["attestation_path"]=str(kp.resolve());partial["kms_attestations"][0]["attestation_sha256"]=h(kp)
    ko=evaluate_manifest(partial)
    affected=[d for d in ko["dossiers"] if d["kms_candidate_id"]==kms[0]["candidate_id"]]
    unaffected=[d for d in ko["dossiers"] if d["kms_candidate_id"]!=kms[0]["candidate_id"]]
    T["partial_kms_blocks_exact_three_pairs"]=len(affected)==3 and all(not d["synthetic_evidence_complete"] for d in affected) and all(d["synthetic_evidence_complete"] for d in unaffected)

    T["repo_internal_manifest_rejected"]=rejected(lambda:run(ROOT/"config/jnu_provider_selection_shortlist_v1.json",td/"x.json"))
    T["repo_internal_output_rejected"]=rejected(lambda:run(mp,ROOT/"composite-should-not-exist.json"))

mem=load(MEMORY);key=load(KEY_CURRENT);terms=load(TERMS_CURRENT);short2=load(SHORTLIST)
T["public_real_ledger_still_zero_zero"]=mem.get("real_live_shadow_forecasts_registered")==0 and mem.get("real_live_shadow_outcomes_registered")==0
T["shortlist_remains_unselected"]=short2.get("selected_market_data_provider")=="UNSELECTED" and short2.get("selected_key_custody_provider")=="UNSELECTED"
T["production_key_still_unselected_disabled"]=key.get("production_enabled") is False and key.get("vendor")=="UNSELECTED" and key.get("region")=="UNSELECTED"
T["real_provider_terms_still_unresolved"]=any(v=="UNRESOLVED" for k,v in terms.items() if k.endswith("_status"))
status="PASS" if all(T.values()) else "FAIL"
print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T)},indent=2))
raise SystemExit(0 if status=="PASS" else 1)
