from __future__ import annotations
import copy, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("m",ROOT/"scripts"/"validate_jnu_entitled_market_data_storage_boundary_v1.py");m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
b=json.loads((ROOT/"config"/"jnu_entitled_market_data_storage_boundary_v1.json").read_text())
B={"entitlement_mode":"OSE_FREE_TRIAL","raw_evidence_storage_scope":"PRIVATE_INTERNAL_ONLY","evidence_destination_class":"PRIVATE_INTERNAL_STORE","target_repository_visibility":"PRIVATE","raw_market_data_in_public_artifact":False,"third_party_cloud_processing_used":False,"third_party_cloud_permission_status":"NOT_APPLICABLE","public_output_requested":False,"public_output_type":"NONE","public_publication_permission_status":"UNCONFIRMED","reconstructive_market_data_fields_in_public_output":False}
T={}
def p(n,x):
    try:T[n]=m.validate(x,b)["status"]=="PASS"
    except Exception:T[n]=False
def f(n,x,s):
    try:m.validate(x,b);T[n]=False
    except RuntimeError as e:T[n]=s in str(e)
p("free_trial_private_local_pass",copy.deepcopy(B))
x=copy.deepcopy(B);x["entitlement_mode"]="LICENSED_REALTIME_VENDOR";p("vendor_private_local_pass",x)
x=copy.deepcopy(B);x["target_repository_visibility"]="PUBLIC";f("public_raw_destination_rejected",x,"public repository")
x=copy.deepcopy(B);x["raw_market_data_in_public_artifact"]=True;f("public_raw_artifact_rejected",x,"raw_market_data_in_public_artifact")
x=copy.deepcopy(B);x["third_party_cloud_processing_used"]=True;x["third_party_cloud_permission_status"]="UNCONFIRMED";f("unapproved_cloud_rejected",x,"explicit approval")
x=copy.deepcopy(B);x["third_party_cloud_processing_used"]=True;x["third_party_cloud_permission_status"]="EXPLICITLY_APPROVED";p("approved_private_cloud_pass",x)
x=copy.deepcopy(B);x["public_output_requested"]=True;x["public_output_type"]="HASH_ATTESTATION";x["public_publication_permission_status"]="UNCONFIRMED";f("unapproved_public_hash_rejected",x,"public output requires")
x=copy.deepcopy(B);x["public_output_requested"]=True;x["public_output_type"]="DERIVED_FORECAST";x["public_publication_permission_status"]="EXPLICITLY_APPROVED";x["reconstructive_market_data_fields_in_public_output"]=True;f("reconstructive_public_derived_rejected",x,"reconstructive")
x=copy.deepcopy(B);x["public_output_requested"]=True;x["public_output_type"]="DERIVED_FORECAST";x["public_publication_permission_status"]="EXPLICITLY_APPROVED";p("explicit_nonreconstructive_public_derived_pass",x)
status="PASS" if all(T.values()) else "FAIL";print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T)},indent=2));raise SystemExit(0 if status=="PASS" else 1)
