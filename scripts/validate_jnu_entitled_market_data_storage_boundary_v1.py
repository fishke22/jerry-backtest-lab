from __future__ import annotations
import argparse, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BOUNDARY=ROOT/"config"/"jnu_entitled_market_data_storage_boundary_v1.json"

def reqbool(x:dict,k:str,v:bool)->None:
    if x.get(k) is not v: raise RuntimeError(f"{k} must be {str(v).lower()}")

def validate(x:dict,b:dict)->dict:
    required=["entitlement_mode","raw_evidence_storage_scope","evidence_destination_class",
              "target_repository_visibility","raw_market_data_in_public_artifact",
              "third_party_cloud_processing_used","third_party_cloud_permission_status",
              "public_output_requested","public_output_type","public_publication_permission_status",
              "reconstructive_market_data_fields_in_public_output"]
    missing=[k for k in required if k not in x]
    if missing: raise RuntimeError("missing required fields: "+",".join(missing))
    mode=x["entitlement_mode"]
    if mode not in b["entitlement_mode_defaults"]: raise RuntimeError("unsupported entitlement_mode")
    if x["raw_evidence_storage_scope"]!="PRIVATE_INTERNAL_ONLY": raise RuntimeError("raw evidence must be PRIVATE_INTERNAL_ONLY")
    if x["evidence_destination_class"]!="PRIVATE_INTERNAL_STORE": raise RuntimeError("raw evidence destination must be PRIVATE_INTERNAL_STORE")
    if str(x["target_repository_visibility"]).upper()=="PUBLIC": raise RuntimeError("public repository cannot be raw evidence destination")
    reqbool(x,"raw_market_data_in_public_artifact",False)
    if x["third_party_cloud_processing_used"] is True and x["third_party_cloud_permission_status"]!="EXPLICITLY_APPROVED":
        raise RuntimeError("third-party cloud processing requires explicit approval")
    public_requested=x["public_output_requested"] is True
    if not public_requested and x["public_output_type"]!="NONE":
        raise RuntimeError("public_output_type must be NONE when no public output is requested")
    if public_requested:
        if x["public_publication_permission_status"]!="EXPLICITLY_APPROVED":
            raise RuntimeError("public output requires explicit OSE/provider permission")
        reqbool(x,"reconstructive_market_data_fields_in_public_output",False)
        if x["public_output_type"] not in {"HASH_ATTESTATION","DERIVED_FORECAST"}:
            raise RuntimeError("unsupported public output type")
    return {
      "version":"1.0","status":"PASS","entitlement_mode":mode,
      "private_raw_evidence_required":True,
      "third_party_cloud_processing_approved":(not x["third_party_cloud_processing_used"] or x["third_party_cloud_permission_status"]=="EXPLICITLY_APPROVED"),
      "public_output_requested":public_requested,
      "public_output_permitted_for_this_manifest":public_requested and x["public_publication_permission_status"]=="EXPLICITLY_APPROVED",
      "real_forecast_created":False,"real_ledger_modified":False
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--manifest",type=Path,required=True);ap.add_argument("--output",type=Path);a=ap.parse_args()
    x=json.loads(a.manifest.read_text(encoding="utf-8"));b=json.loads(BOUNDARY.read_text(encoding="utf-8"))
    out=validate(x,b);s=json.dumps(out,ensure_ascii=False,indent=2)
    if a.output:a.output.write_text(s+"\n",encoding="utf-8")
    print(s)
if __name__=="__main__":main()
