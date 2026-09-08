from __future__ import annotations
import argparse, json
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external, write_replace_json
from attest_jnu_provider_term_evidence_v1 import attest, sha256
from stage_jnu_private_provider_term_evidence_v1 import load

ROOT=Path(__file__).resolve().parents[1]
PROTO=ROOT/"config"/"jnu_private_provider_term_evidence_staging_protocol_v1.json"
SECRET_KEYS={"source_document_path","source_text","raw_text","document_text","quoted_text","credential","credentials","api_key","access_token","password","secret","client_secret","private_key","material_b64","token"}

def forbidden_keys(x,path="root")->list[str]:
    hits=[]
    if isinstance(x,dict):
        for k,v in x.items():
            if str(k).lower() in SECRET_KEYS: hits.append(path+"."+str(k))
            hits.extend(forbidden_keys(v,path+"."+str(k)))
    elif isinstance(x,list):
        for i,v in enumerate(x): hits.extend(forbidden_keys(v,f"{path}[{i}]"))
    return hits

def build_pack(stages:list[dict])->dict:
    if not stages: raise RuntimeError("at least one staging record required")
    pack_id=stages[0]["pack_id"];asof=stages[0]["evidence_as_of"]
    sources=[];claims=[]
    for st in stages:
        if st.get("artifact_class")!="JNU_PRIVATE_PROVIDER_TERM_EVIDENCE_STAGE" or st.get("storage_scope")!="PRIVATE_INTERNAL_ONLY":
            raise RuntimeError("private staging artifact invalid")
        if st.get("mode")!="SYNTHETIC" or st.get("synthetic_fixture") is not True:
            raise RuntimeError("current emitter is synthetic-only")
        if st["pack_id"]!=pack_id or st["evidence_as_of"]!=asof:
            raise RuntimeError("staging records must share pack_id and evidence_as_of")
        if st.get("source_document_text_copied") is not False or st.get("credentials_collected") is not False or st.get("real_entitled_data_ingested") is not False:
            raise RuntimeError("private staging invariant violated")
        src=dict(st["source"])
        p=Path(str(src["source_document_path"]))
        require_external(p,"synthetic term evidence source document")
        if not p.is_file() or sha256(p)!=src["document_sha256"] or sha256(p)!=st["source_document_sha256"]:
            raise RuntimeError("source document changed after staging")
        sources.append(src)
        for c in st["claims"]:
            cc=dict(c);cc["evidence_ids"]=[src["evidence_id"]];claims.append(cc)
    return {"version":"1.0","pack_id":pack_id,"evidence_as_of":asof,"sources":sources,"claims":claims}

def emit(stage_paths:list[Path],output:Path)->dict:
    require_external(output,"redacted provider term attestation output")
    stages=[]
    for p in stage_paths:
        require_external(p,"private provider term evidence staging record")
        if not p.is_file(): raise RuntimeError("private staging record missing")
        stages.append(load(p))
    pack=build_pack(stages)
    att=attest(pack)
    redacted={
      "version":"1.0",
      "artifact_class":"JNU_REDACTED_PROVIDER_TERM_ATTESTATION",
      "storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,
      "mode":"SYNTHETIC",
      "status":att["status"],
      "evidence_as_of":att["evidence_as_of"],
      "pack_id":att["pack_id"],
      "provider_terms":att["provider_terms"],
      "evidence_ledger":att["evidence_ledger"],
      "source_count":att["source_count"],
      "claim_count":att["claim_count"],
      "redaction":{
        "source_document_paths_emitted":False,
        "confidential_source_text_emitted":False,
        "credentials_emitted":False,
        "inferred_permission_used":False
      },
      "real_activation_authorized":False
    }
    hits=forbidden_keys(redacted)
    if hits: raise RuntimeError("redacted attestation contains prohibited key: "+hits[0])
    serialized=json.dumps(redacted,ensure_ascii=False)
    for st in stages:
        marker=st.get("synthetic_confidential_marker")
        if marker and marker in serialized: raise RuntimeError("source text marker leaked into redacted output")
    write_replace_json(output,redacted)
    return {"status":"REDACTED_SYNTHETIC_ATTESTATION_EMITTED","attestation_status":redacted["status"],"source_count":redacted["source_count"],"claim_count":redacted["claim_count"],"source_document_paths_emitted":False,"confidential_source_text_emitted":False,"credentials_emitted":False,"real_activation_authorized":False,"public_output_created":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--stage",type=Path,action="append",required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    print(json.dumps(emit(a.stage,a.output),indent=2))

if __name__=="__main__": main()
