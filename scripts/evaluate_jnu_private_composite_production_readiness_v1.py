from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external, write_replace_json
from evaluate_jnu_production_key_custody_provider_readiness_v1 import evaluate_terms

ROOT=Path(__file__).resolve().parents[1]
PROTO=ROOT/"config"/"jnu_private_composite_production_readiness_join_protocol_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
TERM_PROTO=ROOT/"config"/"jnu_provider_term_readiness_protocol_v1.json"
KMS_PROTO=ROOT/"config"/"jnu_private_kms_deployment_evidence_staging_protocol_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"

PROVIDER_ENTRY_KEYS={"candidate_id","attestation_path","attestation_sha256","binding_assertion","reviewer_attestation"}
KMS_ENTRY_KEYS={"candidate_id","attestation_path","attestation_sha256","reviewer_attestation"}
TOP_KEYS={"version","mode","synthetic_fixture","join_id","evidence_as_of","provider_attestations","kms_attestations"}
HEX64=re.compile(r"^[0-9a-f]{64}$")

def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise RuntimeError(f"{p} must contain an object")
    return x

def sha256_file(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def exact_keys(x:dict,allowed:set[str],label:str)->None:
    extra=set(x)-allowed
    if extra: raise RuntimeError(label+" contains prohibited/unknown fields: "+",".join(sorted(extra)))

def forbidden_keys(x,prohibited:set[str],path="root")->list[str]:
    hits=[]
    if isinstance(x,dict):
        for k,v in x.items():
            if str(k).lower() in prohibited: hits.append(path+"."+str(k))
            hits.extend(forbidden_keys(v,prohibited,path+"."+str(k)))
    elif isinstance(x,list):
        for i,v in enumerate(x): hits.extend(forbidden_keys(v,prohibited,f"{path}[{i}]"))
    return hits

def _shortlist()->tuple[dict,dict,dict]:
    s=load(SHORTLIST)
    return s,{x["id"]:x for x in s["market_data_candidates"]},{x["id"]:x for x in s["key_custody_candidates"]}

def _validate_evidence_hashes(ledger,kind:str)->int:
    if not isinstance(ledger,dict) or not ledger: raise RuntimeError(kind+" evidence ledger required")
    n=0
    for key,val in ledger.items():
        rows=val if isinstance(val,list) else [val]
        if not rows: raise RuntimeError(kind+" evidence ledger entry empty: "+str(key))
        for row in rows:
            if not isinstance(row,dict): raise RuntimeError(kind+" evidence row invalid")
            digest=str(row.get("document_sha256",""))
            if not HEX64.fullmatch(digest): raise RuntimeError(kind+" evidence document SHA-256 invalid")
            n+=1
    return n

def _provider_attestation(entry:dict,proto:dict,term_proto:dict)->dict:
    exact_keys(entry,PROVIDER_ENTRY_KEYS,"provider manifest entry")
    if entry["binding_assertion"]!=proto["manifest"]["provider_binding_assertion"] or entry["reviewer_attestation"]!=proto["manifest"]["reviewer_attestation"]:
        raise RuntimeError("provider candidate binding not explicitly reviewed")
    p=Path(str(entry["attestation_path"]))
    if not p.is_absolute(): raise RuntimeError("provider attestation_path must be absolute")
    require_external(p,"provider redacted attestation")
    if not p.is_file(): raise RuntimeError("provider redacted attestation missing")
    digest=sha256_file(p)
    if digest!=str(entry["attestation_sha256"]): raise RuntimeError("provider redacted attestation SHA mismatch")
    a=load(p)
    if a.get("artifact_class")!=proto["attestation_contracts"]["provider_artifact_class"] or a.get("mode")!="SYNTHETIC":
        raise RuntimeError("provider redacted attestation contract mismatch")
    if a.get("public_distribution_permitted") is not False or a.get("real_activation_authorized") is not False:
        raise RuntimeError("provider redacted attestation violates frozen boundary")
    hits=forbidden_keys(a,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("provider redacted attestation contains prohibited field: "+hits[0])
    evidence_rows=_validate_evidence_hashes(a.get("evidence_ledger"),"provider")
    terms=a.get("provider_terms")
    if not isinstance(terms,dict): raise RuntimeError("provider_terms missing")
    readiness=evaluate_terms(terms,term_proto)
    complete=a.get("status")==proto["attestation_contracts"]["provider_complete_status"] and readiness["status"]=="PASS"
    return {"candidate_id":entry["candidate_id"],"sha256":digest,"pack_id":a.get("pack_id"),"evidence_as_of":a.get("evidence_as_of"),"evidence_rows":evidence_rows,"complete":complete,"blockers":readiness["blockers"] if readiness["status"]!="PASS" else []}

def _kms_attestation(entry:dict,proto:dict,kms_proto:dict)->dict:
    exact_keys(entry,KMS_ENTRY_KEYS,"KMS manifest entry")
    if entry["reviewer_attestation"]!=proto["manifest"]["reviewer_attestation"]: raise RuntimeError("KMS candidate binding not explicitly reviewed")
    p=Path(str(entry["attestation_path"]))
    if not p.is_absolute(): raise RuntimeError("KMS attestation_path must be absolute")
    require_external(p,"KMS redacted attestation")
    if not p.is_file(): raise RuntimeError("KMS redacted attestation missing")
    digest=sha256_file(p)
    if digest!=str(entry["attestation_sha256"]): raise RuntimeError("KMS redacted attestation SHA mismatch")
    a=load(p)
    if a.get("artifact_class")!=proto["attestation_contracts"]["kms_artifact_class"] or a.get("mode")!="SYNTHETIC":
        raise RuntimeError("KMS redacted attestation contract mismatch")
    if a.get("candidate_id")!=entry["candidate_id"]: raise RuntimeError("KMS candidate_id does not match attestation")
    if a.get("public_distribution_permitted") is not False or a.get("real_activation_authorized") is not False:
        raise RuntimeError("KMS redacted attestation violates frozen boundary")
    if a.get("vendor_selection_performed") is not False or a.get("production_profile_modified") is not False:
        raise RuntimeError("KMS redacted attestation indicates forbidden selection/mutation")
    hits=forbidden_keys(a,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("KMS redacted attestation contains prohibited field: "+hits[0])
    evidence_rows=_validate_evidence_hashes(a.get("evidence_ledger"),"KMS")
    required=kms_proto["required_controls"]
    controls=a.get("controls",{})
    blockers=[]
    for ctl,rule in required.items():
        if ctl not in controls:
            blockers.append("KMS_CONTROL_MISSING:"+ctl);continue
        value=controls[ctl].get("value")
        t=rule["type"]
        if t=="boolean" and value is not rule["required_value"]: blockers.append("KMS_CONTROL_INVALID:"+ctl)
        elif t=="integer_min" and (isinstance(value,bool) or not isinstance(value,int) or value<int(rule["minimum"])): blockers.append("KMS_CONTROL_INVALID:"+ctl)
        elif t=="string" and value!=rule["required_value"]: blockers.append("KMS_CONTROL_INVALID:"+ctl)
    complete=a.get("status")==proto["attestation_contracts"]["kms_complete_status"] and not blockers
    return {"candidate_id":entry["candidate_id"],"sha256":digest,"pack_id":a.get("pack_id"),"evidence_as_of":a.get("evidence_as_of"),"evidence_rows":evidence_rows,"complete":complete,"blockers":blockers}

def evaluate_manifest(manifest:dict)->dict:
    proto=load(PROTO);term_proto=load(TERM_PROTO);kms_proto=load(KMS_PROTO);short,pmap,kmap=_shortlist()
    exact_keys(manifest,TOP_KEYS,"composite join manifest")
    if manifest.get("mode")!="SYNTHETIC" or manifest.get("synthetic_fixture") is not True: raise RuntimeError("composite join gate is synthetic-only")
    if not isinstance(manifest.get("join_id"),str) or not manifest["join_id"].startswith("JNU_JOIN_SYNTH_"): raise RuntimeError("synthetic join_id invalid")
    providers=manifest.get("provider_attestations");kms=manifest.get("kms_attestations")
    if not isinstance(providers,list) or len(providers)!=int(proto["manifest"]["exact_provider_attestation_count"]): raise RuntimeError("exactly three provider attestations required")
    if not isinstance(kms,list) or len(kms)!=int(proto["manifest"]["exact_kms_attestation_count"]): raise RuntimeError("exactly two KMS attestations required")
    pids=[x.get("candidate_id") for x in providers];kids=[x.get("candidate_id") for x in kms]
    if len(set(pids))!=len(pids) or len(set(kids))!=len(kids): raise RuntimeError("duplicate candidate_id in composite manifest")
    if set(pids)!=set(pmap): raise RuntimeError("provider attestations must cover exact frozen shortlist")
    if set(kids)!=set(kmap): raise RuntimeError("KMS attestations must cover exact frozen shortlist")
    if short.get("selected_market_data_provider")!="UNSELECTED" or short.get("selected_key_custody_provider")!="UNSELECTED":
        raise RuntimeError("shortlist unexpectedly contains selection")

    p={e["candidate_id"]:_provider_attestation(e,proto,term_proto) for e in providers}
    k={e["candidate_id"]:_kms_attestation(e,proto,kms_proto) for e in kms}
    dossiers=[]
    invariant=list(proto["invariant_activation_blockers"])
    for pc in pmap:
        for kc in kmap:
            pb=list(p[pc]["blockers"]);kb=list(k[kc]["blockers"])
            evidence_complete=p[pc]["complete"] and k[kc]["complete"] and not pb and not kb
            status=proto["combination_rule"]["synthetic_evidence_complete_status"] if evidence_complete else proto["combination_rule"]["synthetic_evidence_blocked_status"]
            blockers=pb+kb+invariant
            dossiers.append({
              "combination_id":pc+"__"+kc,
              "market_data_candidate_id":pc,
              "kms_candidate_id":kc,
              "status":status,
              "synthetic_evidence_complete":evidence_complete,
              "provider_term_blockers":pb,
              "kms_control_blockers":kb,
              "activation_blockers":invariant,
              "lineage":{
                "provider_attestation_sha256":p[pc]["sha256"],
                "provider_pack_id":p[pc]["pack_id"],
                "provider_evidence_rows":p[pc]["evidence_rows"],
                "kms_attestation_sha256":k[kc]["sha256"],
                "kms_pack_id":k[kc]["pack_id"],
                "kms_evidence_rows":k[kc]["evidence_rows"]
              },
              "rank":None,
              "recommended":False,
              "selected":False,
              "real_activation_authorized":False
            })
    if len(dossiers)!=int(proto["combination_rule"]["expected_combination_count"]): raise RuntimeError("cartesian product count mismatch")
    key_current=load(KEY_CURRENT);terms_current=load(TERMS_CURRENT)
    return {
      "version":"1.0",
      "artifact_class":"JNU_PRIVATE_COMPOSITE_PREACTIVATION_READINESS_DOSSIERS",
      "storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,
      "mode":"SYNTHETIC",
      "join_id":manifest["join_id"],
      "evidence_as_of":manifest["evidence_as_of"],
      "combination_count":len(dossiers),
      "dossiers":dossiers,
      "ranking_generated":False,
      "recommendation_generated":False,
      "selection_generated":False,
      "market_data_provider_selected":False,
      "kms_provider_selected":False,
      "production_key_profile_enabled":key_current.get("production_enabled") is True,
      "real_provider_term_current_ready":not any(v=="UNRESOLVED" for key,v in terms_current.items() if key.endswith("_status")),
      "credentials_connected":False,
      "real_activation_manifest_generated":False,
      "real_activation_authorized":False
    }

def run(manifest_path:Path,output:Path)->dict:
    require_external(manifest_path,"composite readiness manifest")
    require_external(output,"composite readiness dossier output")
    if not manifest_path.is_file(): raise RuntimeError("composite readiness manifest missing")
    out=evaluate_manifest(load(manifest_path))
    hits=forbidden_keys(out,set(load(PROTO)["prohibited_keys"]))
    if hits: raise RuntimeError("composite output contains prohibited field: "+hits[0])
    write_replace_json(output,out)
    return {"status":"SYNTHETIC_COMPOSITE_DOSSIERS_EMITTED","combination_count":out["combination_count"],"ranking_generated":False,"recommendation_generated":False,"selection_generated":False,"real_activation_authorized":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    print(json.dumps(run(a.manifest,a.output),indent=2))

if __name__=="__main__": main()
