from __future__ import annotations
import argparse, json
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external, write_replace_json
from stage_jnu_private_kms_deployment_evidence_v1 import load, sha256_file, shortlist_candidates

ROOT=Path(__file__).resolve().parents[1]
PROTO=ROOT/"config"/"jnu_private_kms_deployment_evidence_staging_protocol_v1.json"
PROHIBITED={"source_document_path","source_text","raw_text","document_text","quoted_text","credential","credentials","api_key","access_token","password","secret","client_secret","private_key","material_b64","token","account_id","project_id","subscription_id","tenant_id","key_id","key_arn","resource_name","service_account","role_arn","principal"}

def forbidden_keys(x,path="root")->list[str]:
    hits=[]
    if isinstance(x,dict):
        for k,v in x.items():
            if str(k).lower() in PROHIBITED: hits.append(path+"."+str(k))
            hits.extend(forbidden_keys(v,path+"."+str(k)))
    elif isinstance(x,list):
        for i,v in enumerate(x): hits.extend(forbidden_keys(v,f"{path}[{i}]"))
    return hits

def emit(stage_paths:list[Path],output:Path)->dict:
    proto=load(PROTO); candidates=shortlist_candidates()
    require_external(output,"redacted KMS control attestation output")
    if not stage_paths: raise RuntimeError("at least one private KMS stage record required")
    stages=[]
    for p in stage_paths:
        require_external(p,"private KMS evidence stage record")
        if not p.is_file(): raise RuntimeError("private KMS stage record missing")
        s=load(p)
        if s.get("artifact_class")!="JNU_PRIVATE_KMS_DEPLOYMENT_EVIDENCE_STAGE" or s.get("storage_scope")!="PRIVATE_INTERNAL_ONLY" or s.get("mode")!="SYNTHETIC" or s.get("synthetic_fixture") is not True:
            raise RuntimeError("invalid private KMS staging artifact")
        if s.get("credentials_collected") is not False or s.get("cloud_resource_identifiers_collected") is not False or s.get("kms_api_called") is not False or s.get("key_created") is not False or s.get("vendor_selected") is not False or s.get("production_enabled") is not False:
            raise RuntimeError("private KMS staging invariant violated")
        for src in s["sources"]:
            psrc=Path(str(src["source_document_path"])); require_external(psrc,"synthetic KMS source document")
            if not psrc.is_file() or sha256_file(psrc)!=src["document_sha256"]:
                raise RuntimeError("KMS evidence source changed after staging")
        stages.append(s)
    cid=stages[0]["candidate_id"];pack=stages[0]["pack_id"];asof=stages[0]["evidence_as_of"]
    if cid not in candidates: raise RuntimeError("candidate no longer in shortlist")
    if any(s["candidate_id"]!=cid or s["pack_id"]!=pack or s["evidence_as_of"]!=asof for s in stages):
        raise RuntimeError("KMS stage records must share candidate_id, pack_id and evidence_as_of")

    evidence={}
    controls={}
    conflicts=[]
    for s in stages:
        for src in s["sources"]:
            evidence[src["evidence_id"]]={
              "evidence_id":src["evidence_id"],"source_role":src["source_role"],"source_class":src["source_class"],
              "authority":src["authority"],"source_uri":src["source_uri"],"document_sha256":src["document_sha256"]
            }
        for c in s["claims"]:
            ctl=c["control"]
            entry={"value":c["value"],"evidence_ids":list(c["evidence_ids"]),"locator":c["locator"],"explicitness":c["explicitness"],"reviewer_attestation":c["reviewer_attestation"]}
            if ctl in controls and controls[ctl]["value"]!=entry["value"]: conflicts.append(ctl)
            controls[ctl]=entry
    if conflicts: raise RuntimeError("conflicting cross-stage KMS control claims: "+",".join(sorted(set(conflicts))))

    required=list(proto["required_controls"])
    missing=[x for x in required if x not in controls]
    complete=not missing
    candidate=candidates[cid]
    profile={
      "control_class":controls.get("control_class",{}).get("value","UNATTESTED"),
      "vendor":controls.get("vendor",{}).get("value",candidate["vendor"]),
      "region":controls.get("region",{}).get("value",candidate["proposed_region"]),
      "hsm_backed":controls.get("hsm_backed",{}).get("value",False),
      "fips_security_level":controls.get("fips_security_level",{}).get("value",0),
      "kek_non_exportable":controls.get("kek_non_exportable",{}).get("value",False),
      "symmetric_kek":controls.get("symmetric_kek",{}).get("value",False),
      "plaintext_kek_never_exposed_to_application":controls.get("plaintext_kek_never_exposed_to_application",{}).get("value",False),
      "provider_audit_logging":controls.get("provider_audit_logging",{}).get("value",False),
      "key_rotation_supported":controls.get("key_rotation_supported",{}).get("value",False),
      "previous_key_versions_retained_for_authorized_decrypt":controls.get("previous_key_versions_retained_for_authorized_decrypt",{}).get("value",False),
      "iam_role_separation":controls.get("iam_role_separation",{}).get("value",False),
      "key_admin_separate_from_crypto_user":controls.get("key_admin_separate_from_crypto_user",{}).get("value",False),
      "restore_approver_separate_from_crypto_user":controls.get("restore_approver_separate_from_crypto_user",{}).get("value",False),
      "deletion_protection_or_delayed_destruction":controls.get("deletion_protection_or_delayed_destruction",{}).get("value",False),
      "explicit_region_and_residency_configuration":controls.get("explicit_region_and_residency_configuration",{}).get("value",False),
      "private_network_path_or_equivalent_restriction":controls.get("private_network_path_or_equivalent_restriction",{}).get("value",False),
      "candidate_selected":False,
      "production_enabled":False
    }
    redacted={
      "version":"1.0",
      "artifact_class":"JNU_REDACTED_KMS_DEPLOYMENT_CONTROL_ATTESTATION",
      "storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,
      "mode":"SYNTHETIC",
      "status":"COMPLETE_SYNTHETIC_CONTROL_ATTESTATION" if complete else "PARTIAL_SYNTHETIC_CONTROL_ATTESTATION_BLOCKED",
      "pack_id":pack,"candidate_id":cid,"evidence_as_of":asof,
      "candidate_profile":profile,
      "controls":controls,
      "evidence_ledger":evidence,
      "missing_controls":missing,
      "redaction":{
        "source_document_paths_emitted":False,"source_document_text_emitted":False,"cloud_resource_identifiers_emitted":False,
        "credentials_emitted":False,"key_material_emitted":False
      },
      "vendor_selection_performed":False,
      "production_profile_modified":False,
      "real_activation_authorized":False
    }
    hits=forbidden_keys(redacted)
    if hits: raise RuntimeError("redacted KMS attestation contains prohibited key: "+hits[0])
    write_replace_json(output,redacted)
    return {"status":"REDACTED_SYNTHETIC_KMS_CONTROL_ATTESTATION_EMITTED","attestation_status":redacted["status"],"candidate_id":cid,"control_count":len(controls),"missing_control_count":len(missing),"source_document_paths_emitted":False,"credentials_emitted":False,"cloud_resource_identifiers_emitted":False,"vendor_selection_performed":False,"production_profile_modified":False,"real_activation_authorized":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--stage",type=Path,action="append",required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    print(json.dumps(emit(a.stage,a.output),indent=2))

if __name__=="__main__": main()
