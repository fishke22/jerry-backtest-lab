from __future__ import annotations
import copy, hashlib, json, tempfile
from pathlib import Path
from stage_jnu_private_kms_deployment_evidence_v1 import ROOT, stage, validate_intake, load
from emit_jnu_redacted_kms_deployment_control_attestation_v1 import emit

MEMORY=ROOT/"config"/"jnu_operational_framework_cross_session_memory_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"

def w(p:Path,x): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+"\n",encoding="utf-8")
def h(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def rejected(fn)->bool:
    try: fn(); return False
    except Exception: return True

T={}
with tempfile.TemporaryDirectory(prefix="jnu-kms-stage-") as td0:
    td=Path(td0)
    doc=td/"internal-control.txt";vdoc=td/"vendor-capability.txt"
    marker="SYNTHETIC_KMS_DEPLOYMENT_PRIVATE_MARKER_DO_NOT_EMIT"
    doc.write_text(marker+"\nsynthetic internal deployment-control evidence only\n",encoding="utf-8")
    vdoc.write_text("synthetic vendor capability baseline only\n",encoding="utf-8")
    controls={
      "control_class":"MANAGED_HSM_BACKED_KMS","vendor":"AWS","region":"ap-northeast-1","hsm_backed":True,"fips_security_level":3,
      "kek_non_exportable":True,"symmetric_kek":True,"plaintext_kek_never_exposed_to_application":True,"provider_audit_logging":True,
      "key_rotation_supported":True,"previous_key_versions_retained_for_authorized_decrypt":True,"iam_role_separation":True,
      "key_admin_separate_from_crypto_user":True,"restore_approver_separate_from_crypto_user":True,
      "deletion_protection_or_delayed_destruction":True,"explicit_region_and_residency_configuration":True,
      "private_network_path_or_equivalent_restriction":True
    }
    base={
      "version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,"pack_id":"JNU_KMS_SYNTH_AWS_001","candidate_id":"AWS_KMS_TOKYO","evidence_as_of":"2026-09-08",
      "sources":[
        {"evidence_id":"E_AWS_INTERNAL_001","source_role":"DEPLOYMENT_CONTROL","source_class":"INTERNAL_DEPLOYMENT_ATTESTATION","authority":"INTERNAL_CONTROL_OWNER","source_uri":"urn:jnu:synthetic:kms:aws:internal:001","source_document_path":str(doc.resolve()),"document_sha256":h(doc),"captured_at_utc":"2026-09-08T00:00:00+00:00","confidentiality":"SYNTHETIC_PRIVATE"},
        {"evidence_id":"E_AWS_VENDOR_001","source_role":"CAPABILITY_BASELINE","source_class":"KMS_VENDOR_OFFICIAL_SNAPSHOT","authority":"KMS_VENDOR","source_uri":"urn:jnu:synthetic:kms:aws:vendor:001","source_document_path":str(vdoc.resolve()),"document_sha256":h(vdoc),"captured_at_utc":"2026-09-08T00:01:00+00:00","confidentiality":"SYNTHETIC_PUBLIC_FIXTURE"}
      ],
      "claims":[{"control":k,"value":v,"evidence_ids":["E_AWS_INTERNAL_001","E_AWS_VENDOR_001"],"locator":"CONTROL:"+k,"explicitness":"EXPLICIT_TEXT","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"} for k,v in controls.items()]
    }
    meta=td/"aws-meta.json";stg=td/"aws-stage.json";out=td/"aws-redacted.json";w(meta,base)
    sr=stage(meta,stg);er=emit([stg],out);red=load(out);raw=out.read_text(encoding="utf-8")
    T["aws_stage_pass"]=sr["source_documents_sha256_verified"] is True
    T["aws_complete_control_attestation"]=er["attestation_status"]=="COMPLETE_SYNTHETIC_CONTROL_ATTESTATION" and len(red["controls"])==17
    T["aws_candidate_profile_not_selected"]=red["candidate_profile"]["candidate_selected"] is False and red["vendor_selection_performed"] is False
    T["aws_production_not_enabled"]=red["candidate_profile"]["production_enabled"] is False and red["production_profile_modified"] is False
    T["redacted_has_no_exact_source_path_key"]=all("source_document_path" not in x for x in red["evidence_ledger"].values())
    T["redacted_has_no_private_marker"]=marker not in raw
    T["redacted_has_no_real_cloud_identifiers"]=all(x not in raw for x in ['"account_id"','"project_id"','"key_id"','"key_arn"','"resource_name"','"service_account"','"role_arn"'])
    T["real_activation_false"]=red["real_activation_authorized"] is False

    gdoc=td/"gcp-internal.txt";gdoc.write_text("synthetic GCP internal deployment evidence\n",encoding="utf-8")
    gcontrols=dict(controls);gcontrols["vendor"]="Google Cloud";gcontrols["region"]="asia-northeast1"
    gbase=copy.deepcopy(base);gbase["pack_id"]="JNU_KMS_SYNTH_GCP_001";gbase["candidate_id"]="GCP_CLOUD_HSM_TOKYO"
    gbase["sources"]=[{"evidence_id":"E_GCP_INTERNAL_001","source_role":"DEPLOYMENT_CONTROL","source_class":"INTERNAL_DEPLOYMENT_ATTESTATION","authority":"INTERNAL_CONTROL_OWNER","source_uri":"urn:jnu:synthetic:kms:gcp:internal:001","source_document_path":str(gdoc.resolve()),"document_sha256":h(gdoc),"captured_at_utc":"2026-09-08T00:02:00+00:00","confidentiality":"SYNTHETIC_RESTRICTED"}]
    gbase["claims"]=[{"control":k,"value":v,"evidence_ids":["E_GCP_INTERNAL_001"],"locator":"CONFIG:"+k,"explicitness":"EXPLICIT_TEXT","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"} for k,v in gcontrols.items()]
    gm=td/"gcp-meta.json";gs=td/"gcp-stage.json";go=td/"gcp-redacted.json";w(gm,gbase);stage(gm,gs);ger=emit([gs],go)
    T["gcp_complete_control_attestation"]=ger["attestation_status"]=="COMPLETE_SYNTHETIC_CONTROL_ATTESTATION"

    bad=copy.deepcopy(base);bad["candidate_id"]="UNKNOWN"
    T["unknown_candidate_rejected"]=rejected(lambda:validate_intake(bad))
    bad=copy.deepcopy(base);bad["claims"]=[dict(x) for x in bad["claims"]];bad["claims"][2]["value"]="us-east-1"
    T["wrong_region_rejected"]=rejected(lambda:validate_intake(bad))
    bad=copy.deepcopy(base);bad["claims"]=[dict(x) for x in bad["claims"]];bad["claims"][1]["value"]="Google Cloud"
    T["wrong_vendor_rejected"]=rejected(lambda:validate_intake(bad))
    bad=copy.deepcopy(base);bad["claims"]=[dict(x) for x in bad["claims"]];bad["claims"][4]["value"]=2
    T["fips_below_three_rejected"]=rejected(lambda:validate_intake(bad))
    bad=copy.deepcopy(base);bad["claims"]=[dict(x) for x in bad["claims"]];bad["claims"][5]["value"]=False
    T["nonexportable_false_rejected"]=rejected(lambda:validate_intake(bad))
    bad=copy.deepcopy(base);bad["mode"]="REAL";bad["synthetic_fixture"]=False
    T["real_mode_rejected"]=rejected(lambda:validate_intake(bad))
    bad=copy.deepcopy(base);bad["account_id"]="123456789012"
    T["cloud_account_identifier_rejected"]=rejected(lambda:validate_intake(bad))
    bad=copy.deepcopy(base);bad["key_id"]="synthetic-key"
    T["key_identifier_field_rejected"]=rejected(lambda:validate_intake(bad))
    bad=copy.deepcopy(base);bad["api_key"]="x"
    T["credential_field_rejected"]=rejected(lambda:validate_intake(bad))
    bad=copy.deepcopy(base);bad["sources"]=[dict(x) for x in bad["sources"]];bad["sources"][0]["document_sha256"]="0"*64
    T["wrong_sha_rejected"]=rejected(lambda:validate_intake(bad))
    bad=copy.deepcopy(base);bad["sources"]=[dict(x) for x in bad["sources"]];bad["sources"][0]["source_document_path"]=str((ROOT/"README.md").resolve());bad["sources"][0]["document_sha256"]=h(ROOT/"README.md")
    T["repo_internal_source_rejected"]=rejected(lambda:validate_intake(bad))
    bad=copy.deepcopy(base);bad["sources"]=[dict(x) for x in bad["sources"]];bad["sources"][0]["authority"]="KMS_VENDOR";bad["sources"][0]["source_class"]="KMS_VENDOR_OFFICIAL_SNAPSHOT"
    T["vendor_source_cannot_promote_deployment_rejected"]=rejected(lambda:validate_intake(bad))
    vendor_only=copy.deepcopy(base);vendor_only["sources"]=[vendor_only["sources"][1]]
    vendor_only["claims"]=[{**x,"evidence_ids":["E_AWS_VENDOR_001"]} for x in vendor_only["claims"]]
    T["capability_only_claims_rejected"]=rejected(lambda:validate_intake(vendor_only))
    bad=copy.deepcopy(base);bad["claims"]=[dict(x) for x in bad["claims"]];bad["claims"][0]["locator"]="full copied sentence"
    T["free_text_locator_rejected"]=rejected(lambda:validate_intake(bad))
    bad=copy.deepcopy(base);bad["claims"]=[dict(x) for x in bad["claims"]];bad["claims"][0]["reviewer_attestation"]="INFERRED"
    T["inferred_attestation_rejected"]=rejected(lambda:validate_intake(bad))
    partial=copy.deepcopy(base);partial["claims"]=partial["claims"][:-1];pm=td/"partial-meta.json";ps=td/"partial-stage.json";po=td/"partial-out.json";w(pm,partial);stage(pm,ps);per=emit([ps],po)
    T["missing_control_emits_partial_blocked"]=per["attestation_status"]=="PARTIAL_SYNTHETIC_CONTROL_ATTESTATION_BLOCKED"
    doc.write_text(marker+"\ntampered after staging\n",encoding="utf-8")
    T["post_stage_tamper_rejected"]=rejected(lambda:emit([stg],td/"tampered-out.json"))
    doc.write_text(marker+"\nsynthetic internal deployment-control evidence only\n",encoding="utf-8")

    st=load(stg);st2=copy.deepcopy(st);st2["claims"]=[{"control":"region","value":"ap-northeast-1","evidence_ids":["E_AWS_INTERNAL_001"],"locator":"CONTROL:region","explicitness":"EXPLICIT_TEXT","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"}]
    # Mutate a stage-only fixture to create an impossible cross-stage conflict after staging validation.
    st2["claims"][0]["value"]="conflicting-region"
    cs=td/"conflict-stage.json";w(cs,st2)
    T["cross_stage_conflict_rejected"]=rejected(lambda:emit([stg,cs],td/"conflict-out.json"))
    T["repo_internal_output_rejected"]=rejected(lambda:emit([stg],ROOT/"kms-should-not-exist.json"))

mem=load(MEMORY);key=load(KEY_CURRENT);short=load(SHORTLIST)
T["public_real_ledger_still_zero_zero"]=mem.get("real_live_shadow_forecasts_registered")==0 and mem.get("real_live_shadow_outcomes_registered")==0
T["production_key_profile_unchanged_unselected"]=key.get("production_enabled") is False and key.get("vendor")=="UNSELECTED" and key.get("region")=="UNSELECTED"
T["shortlist_still_unselected"]=short.get("selected_key_custody_provider")=="UNSELECTED"
status="PASS" if all(T.values()) else "FAIL"
print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T)},indent=2))
raise SystemExit(0 if status=="PASS" else 1)
