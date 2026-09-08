from __future__ import annotations
import argparse,json,re
from pathlib import Path
from jnu_integrity_hash_v1 import canonical_text_sha256
from evaluate_jnu_production_key_custody_provider_readiness_v1 import evaluate
ROOT=Path(__file__).resolve().parents[1]
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
FRAMEWORK=ROOT/"config"/"jnu_operational_framework_current_v1_9.json"
SECRET_RE=re.compile(r"(secret|password|api[_-]?key|access[_-]?token|credential|private[_-]?key)",re.I)

def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict):raise RuntimeError(f"{p} must contain an object")
    return x
def secret_walk(x,path="$"):
    hits=[]
    if isinstance(x,dict):
        for k,v in x.items():
            if SECRET_RE.search(str(k)):hits.append(path+"."+str(k))
            hits.extend(secret_walk(v,path+"."+str(k)))
    elif isinstance(x,list):
        for i,v in enumerate(x):hits.extend(secret_walk(v,f"{path}[{i}]"))
    return hits

def generate(key:dict,att:dict,selection:dict,mode:str)->dict:
    terms=att.get("provider_terms")
    if not isinstance(terms,dict):raise RuntimeError("provider term attestation missing provider_terms")
    if att.get("status")!="COMPLETE_EXPLICIT_TERMS":raise RuntimeError("provider term attestation is not complete explicit terms")
    r=evaluate(key,terms)
    if r["status"]!="READY_FOR_REAL_ENCRYPTED_BACKUP_PRIVATE_ONLY":raise RuntimeError("production readiness evaluator blocked activation")
    if selection.get("market_data_selection_status")!="EXPLICITLY_SELECTED" or selection.get("key_custody_selection_status")!="EXPLICITLY_SELECTED":
        raise RuntimeError("provider selections are not explicit")
    sl=load(SHORTLIST)
    if mode=="REAL":
        mids={x["id"] for x in sl["market_data_candidates"]};kids={x["id"] for x in sl["key_custody_candidates"]}
        if selection.get("market_data_provider_id") not in mids:raise RuntimeError("market data provider not in frozen shortlist")
        if selection.get("key_custody_provider_id") not in kids:raise RuntimeError("key custody provider not in frozen shortlist")
        kc=next(x for x in sl["key_custody_candidates"] if x["id"]==selection["key_custody_provider_id"])
        if key.get("vendor")!=kc.get("vendor") or key.get("region")!=kc.get("proposed_region"):
            raise RuntimeError("key profile vendor/region does not match selected shortlist candidate")
    elif mode!="SYNTHETIC_DRY_RUN":
        raise RuntimeError("invalid activation generation mode")
    payload={
      "version":"1.0",
      "status":"SYNTHETIC_ACTIVATION_DRY_RUN_READY" if mode!="REAL" else "REAL_PRIVATE_ENCRYPTED_BACKUP_ACTIVATION_READY",
      "mode":mode,
      "authoritative_framework":"config/jnu_operational_framework_current_v1_9.json",
      "framework_sha256":canonical_text_sha256(FRAMEWORK),
      "market_data_provider_id":selection["market_data_provider_id"],
      "key_custody_provider_id":selection["key_custody_provider_id"],
      "key_vendor":key["vendor"],
      "key_region":key["region"],
      "term_attestation_pack_id":att["pack_id"],
      "term_evidence_as_of":att["evidence_as_of"],
      "readiness_evaluator_status":r["status"],
      "public_output_authorized":False,
      "contains_credentials":False,
      "contains_key_material":False,
      "real_market_data_connected":False if mode!="REAL" else True,
      "activation_manifest_is_authorization_record_only":True
    }
    hits=secret_walk(payload)
    if hits:raise RuntimeError("activation manifest secret-like field detected")
    return payload

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--key-profile",type=Path,required=True);ap.add_argument("--term-attestation",type=Path,required=True);ap.add_argument("--selection",type=Path,required=True);ap.add_argument("--mode",choices=["REAL","SYNTHETIC_DRY_RUN"],required=True);ap.add_argument("--output",type=Path);a=ap.parse_args()
    out=generate(load(a.key_profile),load(a.term_attestation),load(a.selection),a.mode);s=json.dumps(out,ensure_ascii=False,indent=2)
    if a.output:a.output.write_text(s+"\n",encoding="utf-8")
    print(s)
if __name__=="__main__":main()
