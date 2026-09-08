from __future__ import annotations
import argparse, hashlib, json, re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit
from jnu_private_atomic_io_v1 import require_external, write_replace_json

ROOT=Path(__file__).resolve().parents[1]
PROTO=ROOT/"config"/"jnu_private_provider_term_evidence_staging_protocol_v1.json"
TERM_PROTO=ROOT/"config"/"jnu_term_evidence_attestation_protocol_v1.json"
TERMS=ROOT/"config"/"jnu_provider_term_readiness_protocol_v1.json"

TOP_KEYS={"version","mode","synthetic_fixture","pack_id","evidence_as_of","subject_id","source","claims"}
SOURCE_KEYS={"evidence_id","source_class","authority","source_uri","source_document_path","document_sha256","captured_at_utc","confidentiality"}
CLAIM_KEYS={"field","value","locator","explicitness","reviewer_attestation"}
SECRET_KEYS={"credential","credentials","api_key","access_token","password","secret","client_secret","private_key","material_b64","token"}
SECRET_VALUE_RE=re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|password|client[_-]?secret|secret|token)\s*=")

def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise RuntimeError(f"{p} must contain an object")
    return x

def sha256_file(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def _check_exact_keys(obj:dict, allowed:set[str], label:str)->None:
    extra=set(obj)-allowed
    if extra: raise RuntimeError(label+" contains prohibited/unknown fields: "+",".join(sorted(extra)))

def _scan_secret_keys(x,path="root")->list[str]:
    hits=[]
    if isinstance(x,dict):
        for k,v in x.items():
            if str(k).lower() in SECRET_KEYS: hits.append(path+"."+str(k))
            hits.extend(_scan_secret_keys(v,path+"."+str(k)))
    elif isinstance(x,list):
        for i,v in enumerate(x): hits.extend(_scan_secret_keys(v,f"{path}[{i}]"))
    return hits

def _validate_uri(uri:str,prefix:str)->None:
    if not uri.startswith(prefix): raise RuntimeError("synthetic source_uri must use frozen synthetic URN prefix")
    if SECRET_VALUE_RE.search(uri) or "@" in urlsplit(uri.replace("urn:","https://",1)).netloc:
        raise RuntimeError("source_uri appears to contain credential-like material")

def _validate_time(s:str)->None:
    d=datetime.fromisoformat(s)
    if d.tzinfo is None: raise RuntimeError("captured_at_utc must be timezone-aware")

def validate_intake(meta:dict)->dict:
    proto=load(PROTO);tp=load(TERM_PROTO);terms=load(TERMS)
    _check_exact_keys(meta,TOP_KEYS,"intake")
    hits=_scan_secret_keys(meta)
    if hits: raise RuntimeError("secret-like field prohibited: "+hits[0])
    if meta.get("mode")!="SYNTHETIC" or meta.get("synthetic_fixture") is not True:
        raise RuntimeError("current staging pipeline is synthetic-only")
    if not isinstance(meta.get("pack_id"),str) or not meta["pack_id"].startswith("JNU_TERM_SYNTH_"):
        raise RuntimeError("synthetic pack_id invalid")
    date.fromisoformat(str(meta["evidence_as_of"]))
    if not isinstance(meta.get("subject_id"),str) or not meta["subject_id"]:
        raise RuntimeError("subject_id required")

    source=meta.get("source")
    if not isinstance(source,dict): raise RuntimeError("source object required")
    _check_exact_keys(source,SOURCE_KEYS,"source")
    missing=[k for k in tp["required_source_fields"] if k not in source]
    if missing: raise RuntimeError("missing source fields: "+",".join(missing))
    if source["source_class"] not in tp["source_classes"] or source["authority"] not in tp["allowed_authorities"]:
        raise RuntimeError("invalid source class/authority")
    if source["confidentiality"] not in proto["private_staging"]["allowed_confidentiality"]:
        raise RuntimeError("invalid synthetic confidentiality classification")
    _validate_uri(str(source["source_uri"]),proto["private_staging"]["synthetic_source_uri_prefix"])
    _validate_time(str(source["captured_at_utc"]))
    p=Path(str(source["source_document_path"]))
    if not p.is_absolute(): raise RuntimeError("source_document_path must be absolute")
    require_external(p,"synthetic term evidence source document")
    if not p.is_file(): raise RuntimeError("synthetic term evidence source document missing")
    actual=sha256_file(p)
    if actual!=str(source["document_sha256"]): raise RuntimeError("source document SHA-256 mismatch")
    if len(actual)!=64: raise RuntimeError("source document SHA-256 invalid")

    fields=set(terms["required_fields"])
    claims=meta.get("claims")
    if not isinstance(claims,list) or not claims: raise RuntimeError("at least one synthetic claim required")
    seen={}
    for c in claims:
        if not isinstance(c,dict): raise RuntimeError("claim must be object")
        _check_exact_keys(c,CLAIM_KEYS,"claim")
        missing=[k for k in ["field","value","locator","explicitness","reviewer_attestation"] if k not in c]
        if missing: raise RuntimeError("missing claim fields: "+",".join(missing))
        field=str(c["field"])
        if field not in fields: raise RuntimeError("claim targets unknown provider-term field: "+field)
        if c["explicitness"]!=tp["claim_rules"]["explicitness_required"] or c["reviewer_attestation"]!=tp["claim_rules"]["reviewer_attestation_required"]:
            raise RuntimeError("claim explicitness/reviewer attestation invalid")
        allowed=set(tp["authority_requirements"].get(field,[]))
        if allowed and source["authority"] not in allowed:
            raise RuntimeError("source authority not permitted for claim field: "+field)
        value=c["value"]
        if field in tp["hard_boolean_values"]:
            if value is not tp["hard_boolean_values"][field]: raise RuntimeError("hard boolean unsafe value: "+field)
        elif field=="service_facilitator_required":
            if not isinstance(value,bool): raise RuntimeError("service_facilitator_required must be boolean")
        elif value not in tp["ready_status_values"]:
            raise RuntimeError("claim value is not an explicit ready value: "+field)
        loc=c["locator"]
        if not isinstance(loc,str) or not loc or len(loc)>int(proto["private_staging"]["locator_max_chars"]):
            raise RuntimeError("claim locator invalid")
        if "\n" in loc or "\r" in loc or not any(loc.startswith(x) for x in proto["private_staging"]["locator_prefixes"]):
            raise RuntimeError("claim locator must be a compact structural locator, not copied source text")
        if field in seen and seen[field]!=value: raise RuntimeError("conflicting claims inside stage intake: "+field)
        seen[field]=value

    return {"source_path":p,"source_sha256":actual,"source":source,"claims":claims,"protocol":proto}

def stage(meta_path:Path,output:Path)->dict:
    require_external(meta_path,"synthetic evidence intake metadata")
    require_external(output,"private evidence staging record")
    if not meta_path.is_file(): raise RuntimeError("synthetic evidence intake metadata missing")
    meta=load(meta_path);v=validate_intake(meta)
    record={
      "version":"1.0",
      "artifact_class":"JNU_PRIVATE_PROVIDER_TERM_EVIDENCE_STAGE",
      "storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,
      "mode":"SYNTHETIC",
      "synthetic_fixture":True,
      "pack_id":meta["pack_id"],
      "evidence_as_of":meta["evidence_as_of"],
      "subject_id":meta["subject_id"],
      "source":dict(v["source"]),
      "claims":[dict(c) for c in v["claims"]],
      "intake_metadata_sha256":sha256_file(meta_path),
      "source_document_sha256":v["source_sha256"],
      "source_document_text_copied":False,
      "credentials_collected":False,
      "outreach_performed":False,
      "provider_selection_performed":False,
      "real_entitled_data_ingested":False
    }
    write_replace_json(output,record)
    return {"status":"PRIVATE_SYNTHETIC_TERM_EVIDENCE_STAGED","pack_id":record["pack_id"],"evidence_id":record["source"]["evidence_id"],"claim_count":len(record["claims"]),"source_document_sha256_verified":True,"source_text_printed":False,"credentials_printed":False,"public_output_created":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--intake-metadata",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    print(json.dumps(stage(a.intake_metadata,a.output),indent=2))

if __name__=="__main__": main()
