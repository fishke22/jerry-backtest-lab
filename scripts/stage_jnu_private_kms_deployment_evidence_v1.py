from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external, write_replace_json

ROOT=Path(__file__).resolve().parents[1]
PROTO=ROOT/"config"/"jnu_private_kms_deployment_evidence_staging_protocol_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"

TOP_KEYS={"version","mode","synthetic_fixture","pack_id","candidate_id","evidence_as_of","sources","claims"}
SOURCE_KEYS={"evidence_id","source_role","source_class","authority","source_uri","source_document_path","document_sha256","captured_at_utc","confidentiality"}
CLAIM_KEYS={"control","value","evidence_ids","locator","explicitness","reviewer_attestation"}
PROHIBITED={"credential","credentials","api_key","access_token","password","secret","client_secret","private_key","material_b64","token","account_id","project_id","subscription_id","tenant_id","key_id","key_arn","resource_name","service_account","role_arn","principal"}

def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise RuntimeError(f"{p} must contain an object")
    return x

def sha256_file(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def exact_keys(x:dict,allowed:set[str],label:str)->None:
    extra=set(x)-allowed
    if extra: raise RuntimeError(label+" contains prohibited/unknown fields: "+",".join(sorted(extra)))

def forbidden_keys(x,path="root")->list[str]:
    hits=[]
    if isinstance(x,dict):
        for k,v in x.items():
            if str(k).lower() in PROHIBITED: hits.append(path+"."+str(k))
            hits.extend(forbidden_keys(v,path+"."+str(k)))
    elif isinstance(x,list):
        for i,v in enumerate(x): hits.extend(forbidden_keys(v,f"{path}[{i}]"))
    return hits

def shortlist_candidates()->dict:
    s=load(SHORTLIST)
    return {x["id"]:x for x in s["key_custody_candidates"]}

def validate_value(control:str,value,candidate:dict,rule:dict)->None:
    t=rule["type"]
    if t=="boolean":
        if value is not rule["required_value"]: raise RuntimeError("control does not satisfy frozen required value: "+control)
    elif t=="integer_min":
        if isinstance(value,bool) or not isinstance(value,int) or value<int(rule["minimum"]): raise RuntimeError("control below frozen minimum: "+control)
    elif t=="string":
        if value!=rule["required_value"]: raise RuntimeError("control string does not satisfy frozen required value: "+control)
    elif t=="candidate_vendor":
        if value!=candidate["vendor"]: raise RuntimeError("vendor claim does not match shortlisted candidate")
    elif t=="candidate_region":
        if value!=candidate["proposed_region"]: raise RuntimeError("region claim does not match shortlisted candidate")
    else: raise RuntimeError("unknown control rule type: "+str(t))

def validate_intake(meta:dict)->dict:
    proto=load(PROTO); candidates=shortlist_candidates()
    exact_keys(meta,TOP_KEYS,"KMS deployment intake")
    hits=forbidden_keys(meta)
    if hits: raise RuntimeError("prohibited cloud/secret identifier field: "+hits[0])
    if meta.get("mode")!="SYNTHETIC" or meta.get("synthetic_fixture") is not True:
        raise RuntimeError("KMS deployment staging is synthetic-only")
    if not isinstance(meta.get("pack_id"),str) or not meta["pack_id"].startswith("JNU_KMS_SYNTH_"):
        raise RuntimeError("synthetic KMS pack_id invalid")
    cid=meta.get("candidate_id")
    if cid not in proto["candidates"] or cid not in candidates: raise RuntimeError("KMS candidate not in frozen shortlist")
    expected=proto["candidates"][cid]; candidate=candidates[cid]
    if candidate.get("vendor")!=expected["vendor"] or candidate.get("proposed_region")!=expected["region"] or candidate.get("control_class")!=expected["control_class"]:
        raise RuntimeError("shortlist candidate identity drift")
    datetime.fromisoformat(str(meta["evidence_as_of"])+"T00:00:00+00:00")

    srcs=meta.get("sources")
    if not isinstance(srcs,list) or not srcs: raise RuntimeError("at least one evidence source required")
    sources={}
    for s in srcs:
        if not isinstance(s,dict): raise RuntimeError("source must be object")
        exact_keys(s,SOURCE_KEYS,"KMS evidence source")
        if s["source_role"] not in proto["evidence_rules"]["allowed_source_roles"]: raise RuntimeError("invalid evidence source role")
        if s["source_class"] not in proto["evidence_rules"]["allowed_source_classes"]: raise RuntimeError("invalid evidence source class")
        if s["authority"] not in proto["evidence_rules"]["allowed_authorities"]: raise RuntimeError("invalid evidence authority")
        if s["source_role"]=="DEPLOYMENT_CONTROL":
            if s["source_class"]!=proto["evidence_rules"]["deployment_control_promoting_source_class"] or s["authority"]!=proto["evidence_rules"]["deployment_control_promoting_authority"]:
                raise RuntimeError("deployment control evidence must be INTERNAL_CONTROL_OWNER / INTERNAL_DEPLOYMENT_ATTESTATION")
        if s["source_role"]=="CAPABILITY_BASELINE" and s["authority"]!="KMS_VENDOR":
            raise RuntimeError("capability baseline must be KMS_VENDOR authority")
        eid=str(s["evidence_id"])
        if not eid or eid in sources: raise RuntimeError("missing/duplicate evidence_id")
        if not str(s["source_uri"]).startswith("urn:jnu:synthetic:kms:"): raise RuntimeError("source_uri must be synthetic KMS URN")
        d=datetime.fromisoformat(str(s["captured_at_utc"]))
        if d.tzinfo is None: raise RuntimeError("captured_at_utc must be timezone-aware")
        if s["confidentiality"] not in {"SYNTHETIC_PRIVATE","SYNTHETIC_RESTRICTED","SYNTHETIC_PUBLIC_FIXTURE"}: raise RuntimeError("invalid synthetic confidentiality")
        p=Path(str(s["source_document_path"]))
        if not p.is_absolute(): raise RuntimeError("source_document_path must be absolute")
        require_external(p,"synthetic KMS deployment evidence source")
        if not p.is_file(): raise RuntimeError("synthetic KMS evidence source missing")
        actual=sha256_file(p)
        if actual!=str(s["document_sha256"]): raise RuntimeError("KMS evidence source SHA-256 mismatch")
        sources[eid]=s

    claims=meta.get("claims")
    if not isinstance(claims,list) or not claims: raise RuntimeError("at least one KMS control claim required")
    seen={}
    controls=proto["required_controls"]
    for c in claims:
        if not isinstance(c,dict): raise RuntimeError("claim must be object")
        exact_keys(c,CLAIM_KEYS,"KMS control claim")
        control=str(c.get("control"))
        if control not in controls: raise RuntimeError("unknown KMS deployment control: "+control)
        if c.get("explicitness")!=proto["evidence_rules"]["explicitness_required"] or c.get("reviewer_attestation")!=proto["evidence_rules"]["reviewer_attestation_required"]:
            raise RuntimeError("KMS control claim not explicitly reviewed")
        eids=c.get("evidence_ids")
        if not isinstance(eids,list) or not eids or any(e not in sources for e in eids): raise RuntimeError("KMS control claim evidence missing")
        promoting=[sources[e] for e in eids if sources[e]["source_role"]=="DEPLOYMENT_CONTROL"]
        if not promoting: raise RuntimeError("vendor capability evidence alone may not promote deployment control: "+control)
        loc=c.get("locator")
        if not isinstance(loc,str) or not loc or len(loc)>int(proto["evidence_rules"]["locator_max_chars"]) or "\n" in loc or "\r" in loc:
            raise RuntimeError("KMS claim locator invalid")
        if not any(loc.startswith(p) for p in proto["evidence_rules"]["locator_prefixes"]): raise RuntimeError("KMS claim locator must be structural")
        validate_value(control,c.get("value"),candidate,controls[control])
        if control in seen and seen[control]!=c.get("value"): raise RuntimeError("conflicting KMS control claim: "+control)
        seen[control]=c.get("value")
    return {"proto":proto,"candidate":candidate,"sources":sources,"claims":claims}

def stage(meta_path:Path,output:Path)->dict:
    require_external(meta_path,"synthetic KMS intake metadata")
    require_external(output,"private KMS evidence stage record")
    if not meta_path.is_file(): raise RuntimeError("synthetic KMS intake metadata missing")
    meta=load(meta_path);v=validate_intake(meta)
    record={
      "version":"1.0",
      "artifact_class":"JNU_PRIVATE_KMS_DEPLOYMENT_EVIDENCE_STAGE",
      "storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,
      "mode":"SYNTHETIC",
      "synthetic_fixture":True,
      "pack_id":meta["pack_id"],
      "candidate_id":meta["candidate_id"],
      "evidence_as_of":meta["evidence_as_of"],
      "candidate_identity":{
        "vendor":v["candidate"]["vendor"],
        "region":v["candidate"]["proposed_region"],
        "control_class":v["candidate"]["control_class"]
      },
      "sources":[dict(s) for s in v["sources"].values()],
      "claims":[dict(c) for c in v["claims"]],
      "intake_metadata_sha256":sha256_file(meta_path),
      "source_documents_sha256_verified":True,
      "source_document_text_copied":False,
      "credentials_collected":False,
      "cloud_resource_identifiers_collected":False,
      "kms_api_called":False,
      "key_created":False,
      "vendor_selected":False,
      "production_enabled":False
    }
    write_replace_json(output,record)
    return {"status":"PRIVATE_SYNTHETIC_KMS_DEPLOYMENT_EVIDENCE_STAGED","candidate_id":record["candidate_id"],"source_count":len(record["sources"]),"claim_count":len(record["claims"]),"source_documents_sha256_verified":True,"kms_api_called":False,"key_created":False,"vendor_selected":False,"production_enabled":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--intake-metadata",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    print(json.dumps(stage(a.intake_metadata,a.output),indent=2))

if __name__=="__main__": main()
