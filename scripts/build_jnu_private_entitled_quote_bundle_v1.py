from __future__ import annotations
import argparse, json, os, uuid
from pathlib import Path
from validate_jnu_entitled_exact_micro_evidence_v1 import validate as validate_quote
from validate_jnu_entitled_market_data_storage_boundary_v1 import validate as validate_boundary

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"config"/"jnu_exact_micro_entitled_source_adapter_contract_v1.json"
ROLL=ROOT/"config"/"jnu_exact_micro_contract_roll_calendar_v1.json"
BOUNDARY=ROOT/"config"/"jnu_entitled_market_data_storage_boundary_v1.json"

def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise RuntimeError(f"{p} must contain an object")
    return x

def under_repo(p:Path)->bool:
    rp=p.resolve()
    rr=ROOT.resolve()
    return rp==rr or rr in rp.parents

def require_external_private_path(p:Path,label:str)->None:
    if under_repo(p):
        raise RuntimeError(f"{label} must resolve outside the public repository")

def build(evidence_path:Path,manifest_path:Path,private_store_root:Path)->dict:
    require_external_private_path(evidence_path,"evidence input")
    require_external_private_path(manifest_path,"permission manifest")
    require_external_private_path(private_store_root,"private store root")
    evidence=load(evidence_path)
    manifest=load(manifest_path)
    if manifest.get("public_output_requested") is not False or manifest.get("public_output_type")!="NONE":
        raise RuntimeError("private quote bridge prohibits public output requests")
    contract=load(CONTRACT);roll=load(ROLL);boundary=load(BOUNDARY)
    quote_validation=validate_quote(evidence,contract,roll)
    boundary_validation=validate_boundary(manifest,boundary)
    receipt_id="JNU_PRIV_"+uuid.uuid4().hex
    outdir=private_store_root.resolve()/"quote_receipts"
    require_external_private_path(outdir,"private quote receipt directory")
    outdir.mkdir(parents=True,exist_ok=True)
    out=outdir/f"{receipt_id}.json"
    bundle={
      "version":"1.0",
      "artifact_class":"JNU_PRIVATE_ENTITLED_QUOTE_BUNDLE",
      "receipt_id":receipt_id,
      "storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,
      "public_hash_attestation_created":False,
      "public_derived_forecast_created":False,
      "formal_forecast_created":False,
      "real_ledger_modified":False,
      "quote_validation":quote_validation,
      "storage_boundary_validation":boundary_validation,
      "raw_entitled_quote_evidence":evidence
    }
    out.write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    try: os.chmod(out,0o600)
    except OSError: pass
    return {"receipt_id":receipt_id,"bundle_path":str(out)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--evidence",type=Path,required=True)
    ap.add_argument("--permission-manifest",type=Path,required=True)
    ap.add_argument("--private-store-root",type=Path,required=True)
    a=ap.parse_args()
    result=build(a.evidence,a.permission_manifest,a.private_store_root)
    print(json.dumps({
      "status":"PRIVATE_ENTITLED_QUOTE_BUNDLE_CREATED",
      "receipt_id":result["receipt_id"],
      "raw_evidence_not_printed":True,
      "formal_forecast_created":False,
      "real_ledger_modified":False
    },ensure_ascii=False,indent=2))
if __name__=="__main__":main()
