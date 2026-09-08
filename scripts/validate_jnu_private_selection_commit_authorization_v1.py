from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external, write_immutable_json, verify_backup, sha256_file

ROOT=Path(__file__).resolve().parents[1]
PROTO=ROOT/"config"/"jnu_private_selection_transition_commit_authorization_protocol_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"

MANIFEST_KEYS={
  "version","mode","synthetic_fixture","ceremony_id","evaluation_at_utc",
  "review_store_root","review_receipt_path","review_receipt_sha256",
  "prepare_store_root","changeset_path","changeset_sha256",
  "decision_store_root","decision_record_path","decision_record_sha256",
  "authorization_path","authorization_sha256"
}
AUTH_KEYS={
  "version","artifact_class","mode","synthetic_fixture","authorization_id","authorization_scope","authorization_status",
  "authorizer_role","authorizer_reference","authorizer_attestation","review_receipt_sha256","changeset_sha256",
  "decision_record_sha256","requested_combination_id","lifecycle_event_count","lifecycle_head_sha256",
  "production_state_cas_sha256","issued_at_utc","valid_from_utc","expires_at_utc",
  "commit_authorized","apply_authorized","execution_capability"
}
SNAPSHOT_IDS={"PROVIDER_SELECTION_SHORTLIST","PRODUCTION_KEY_CUSTODY_CURRENT","PROVIDER_TERM_READINESS_CURRENT"}
HEX64=re.compile(r"^[0-9a-f]{64}$")
CEREMONY_RE=re.compile(r"^JNU_COMMIT_AUTH_CEREMONY_SYNTH_[A-Za-z0-9_-]+$")

def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise RuntimeError(f"{p} must contain an object")
    return x

def exact_keys(x:dict,allowed:set[str],label:str)->None:
    extra=set(x)-allowed; missing=allowed-set(x)
    if extra: raise RuntimeError(label+" contains prohibited/unknown fields: "+",".join(sorted(extra)))
    if missing: raise RuntimeError(label+" missing required fields: "+",".join(sorted(missing)))

def forbidden_keys(x,prohibited:set[str],path="root")->list[str]:
    hits=[]
    if isinstance(x,dict):
        for k,v in x.items():
            if str(k).lower() in prohibited: hits.append(path+"."+str(k))
            hits.extend(forbidden_keys(v,prohibited,path+"."+str(k)))
    elif isinstance(x,list):
        for i,v in enumerate(x): hits.extend(forbidden_keys(v,prohibited,f"{path}[{i}]"))
    return hits

def parse_time(value,label:str):
    from datetime import datetime
    try:d=datetime.fromisoformat(str(value))
    except Exception as e: raise RuntimeError(label+" invalid") from e
    if d.tzinfo is None: raise RuntimeError(label+" must be timezone-aware")
    return d

def validate_external_record(root:Path,path:Path,expected_sha:str,subdir:str,label:str)->dict:
    require_external(root,label+" store");require_external(path,label)
    if not root.is_absolute() or not path.is_absolute(): raise RuntimeError(label+" store/path must be absolute")
    root=root.resolve();path=path.resolve()
    if path.parent!=(root/subdir).resolve(): raise RuntimeError(label+" must be inside canonical store subdirectory")
    if not path.is_file(): raise RuntimeError(label+" missing")
    if not HEX64.fullmatch(expected_sha): raise RuntimeError(label+" SHA-256 invalid")
    if sha256_file(path)!=expected_sha: raise RuntimeError(label+" SHA-256 mismatch")
    if verify_backup(root,path).get("status")!="PASS": raise RuntimeError(label+" immutable backup/checksum invalid")
    return load(path)

def validate_review_receipt(m:dict,proto:dict,evaluation)->dict:
    r=validate_external_record(Path(str(m["review_store_root"])),Path(str(m["review_receipt_path"])),str(m["review_receipt_sha256"]),"prepare_review_receipts","PREPARE review receipt")
    c=proto["review_receipt_contract"]
    for k in ["artifact_class","storage_scope","public_distribution_permitted","mode","outcome","review_count","commit_capability","apply_capability","selection_transition_permitted","selection_written","selected_combination_id","production_state_mutated","real_activation_authorized","cas_revalidated_at_review","cas_state_fresh"]:
        expected=c["required_outcome"] if k=="outcome" else c[k]
        if r.get(k)!=expected: raise RuntimeError("PREPARE review receipt contract mismatch: "+k)
    reviews=r.get("reviews")
    if not isinstance(reviews,list) or len(reviews)!=2: raise RuntimeError("PREPARE review receipt reviews invalid")
    for x in reviews:
        if x.get("disposition")!="APPROVE": raise RuntimeError("PREPARE review receipt is not dual APPROVE")
        reviewed=parse_time(x.get("reviewed_at_utc"),"reviewed_at_utc")
        reval=parse_time(x.get("revalidation_due_at_utc"),"revalidation_due_at_utc")
        expiry=parse_time(x.get("expires_at_utc"),"expires_at_utc")
        if evaluation<reviewed: raise RuntimeError("ceremony evaluation precedes review")
        if evaluation>=reval or evaluation>expiry: raise RuntimeError("PREPARE review receipt stale or expired at ceremony")
    hits=forbidden_keys(r,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("PREPARE review receipt contains prohibited field: "+hits[0])
    return r

def validate_changeset(m:dict,review:dict,proto:dict)->dict:
    c=validate_external_record(Path(str(m["prepare_store_root"])),Path(str(m["changeset_path"])),str(m["changeset_sha256"]),"selection_transition_prepares","PREPARE changeset")
    if c.get("artifact_class")!="JNU_SYNTHETIC_SELECTION_TRANSITION_PREPARE_CHANGESET" or c.get("status")!="SYNTHETIC_PREPARE_ONLY_CHANGESET_READY_NOT_COMMITTABLE":
        raise RuntimeError("PREPARE changeset contract mismatch")
    for k,v in [("commit_capability",False),("apply_capability",False),("selection_transition_permitted",False),("selection_written",False),("selected_combination_id","UNSELECTED"),("production_state_mutated",False),("real_activation_authorized",False)]:
        if c.get(k)!=v: raise RuntimeError("PREPARE changeset boundary mismatch: "+k)
    if review.get("changeset_sha256")!=m["changeset_sha256"] or review.get("prepare_id")!=c.get("prepare_id"):
        raise RuntimeError("review receipt / PREPARE changeset lineage mismatch")
    if review.get("requested_combination_id")!=c.get("requested_combination_id"):
        raise RuntimeError("review receipt / PREPARE pair mismatch")
    return c

def validate_decision(m:dict,review:dict,changeset:dict)->dict:
    d=validate_external_record(Path(str(m["decision_store_root"])),Path(str(m["decision_record_path"])),str(m["decision_record_sha256"]),"selection_lifecycle_decisions","lifecycle-integrated decision")
    if d.get("artifact_class")!="JNU_SYNTHETIC_SELECTION_DECISION_LIFECYCLE_CURRENT_AUTH_RECORD" or d.get("status")!="SYNTHETIC_LIFECYCLE_CURRENT_AUTH_VALIDATED_NO_SELECTION":
        raise RuntimeError("decision contract mismatch")
    for k,v in [("selection_transition_permitted",False),("selection_written",False),("selected_combination_id","UNSELECTED"),("production_state_mutated",False),("real_activation_authorized",False)]:
        if d.get(k)!=v: raise RuntimeError("decision boundary mismatch: "+k)
    if review.get("decision_record_sha256")!=m["decision_record_sha256"] or changeset.get("decision_record_sha256")!=m["decision_record_sha256"]:
        raise RuntimeError("decision SHA lineage mismatch")
    for k in ["decision_id","requested_combination_id","requested_market_data_candidate_id","requested_kms_candidate_id","lifecycle_event_count","lifecycle_head_sha256"]:
        cv=changeset.get(k); dv=d.get(k)
        if k=="decision_id":
            if cv!=dv or review.get("decision_id")!=dv: raise RuntimeError("decision ID lineage mismatch")
        elif cv!=dv or review.get(k)!=dv: raise RuntimeError("decision lineage mismatch: "+k)
    return d

def current_cas(changeset:dict)->dict:
    snaps=changeset.get("production_state_preconditions")
    if not isinstance(snaps,dict) or set(snaps)!=SNAPSHOT_IDS: raise RuntimeError("PREPARE CAS surface invalid")
    paths={
      "PROVIDER_SELECTION_SHORTLIST":SHORTLIST,
      "PRODUCTION_KEY_CUSTODY_CURRENT":KEY_CURRENT,
      "PROVIDER_TERM_READINESS_CURRENT":TERMS_CURRENT
    }
    out={}
    for sid,p in paths.items():
        row=snaps[sid]
        if row.get("path")!=str(p.relative_to(ROOT)): raise RuntimeError("PREPARE CAS path mismatch: "+sid)
        expected=str(row.get("sha256",""))
        if not HEX64.fullmatch(expected): raise RuntimeError("PREPARE CAS SHA invalid: "+sid)
        actual=sha256_file(p)
        if actual!=expected: raise RuntimeError("stale production-state CAS at ceremony: "+sid)
        out[sid]=actual
    short=load(SHORTLIST);key=load(KEY_CURRENT);terms=load(TERMS_CURRENT)
    if short.get("selected_market_data_provider")!="UNSELECTED" or short.get("selected_key_custody_provider")!="UNSELECTED": raise RuntimeError("selection state already mutated")
    if key.get("production_enabled") is not False or key.get("vendor")!="UNSELECTED" or key.get("region")!="UNSELECTED": raise RuntimeError("production key state already mutated")
    if terms.get("broker_auth_used") is not False or terms.get("trading_permission_used") is not False or terms.get("public_output_requested") is not False: raise RuntimeError("provider-term production boundary mutated")
    return out

def validate_authorization(m:dict,review:dict,changeset:dict,decision:dict,cas:dict,proto:dict,evaluation)->dict:
    p=Path(str(m["authorization_path"]))
    require_external(p,"commit authorization artifact")
    if not p.is_absolute() or not p.is_file(): raise RuntimeError("commit authorization artifact missing/invalid path")
    expected=str(m["authorization_sha256"])
    if not HEX64.fullmatch(expected) or sha256_file(p)!=expected: raise RuntimeError("commit authorization artifact SHA-256 mismatch")
    a=load(p); exact_keys(a,AUTH_KEYS,"commit authorization artifact")
    hits=forbidden_keys(a,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("commit authorization artifact contains prohibited field: "+hits[0])
    c=proto["authorization_contract"]
    for k in ["artifact_class","mode","synthetic_fixture","authorization_scope","authorization_status","authorizer_role","authorizer_attestation","commit_authorized","apply_authorized","execution_capability"]:
        if a.get(k)!=c[k]: raise RuntimeError("commit authorization frozen value mismatch: "+k)
    if not str(a.get("authorizer_reference","")): raise RuntimeError("authorizer_reference required")
    issued=parse_time(a.get("issued_at_utc"),"authorization issued_at_utc"); valid=parse_time(a.get("valid_from_utc"),"authorization valid_from_utc"); expiry=parse_time(a.get("expires_at_utc"),"authorization expires_at_utc")
    if issued>valid or valid>evaluation or evaluation>=expiry: raise RuntimeError("commit authorization not current at ceremony")
    bindings=[
      ("review_receipt_sha256",m["review_receipt_sha256"]),
      ("changeset_sha256",m["changeset_sha256"]),
      ("decision_record_sha256",m["decision_record_sha256"]),
      ("requested_combination_id",changeset["requested_combination_id"]),
      ("lifecycle_event_count",changeset["lifecycle_event_count"]),
      ("lifecycle_head_sha256",changeset["lifecycle_head_sha256"])
    ]
    for k,v in bindings:
        if a.get(k)!=v: raise RuntimeError("commit authorization binding mismatch: "+k)
    acas=a.get("production_state_cas_sha256")
    if not isinstance(acas,dict) or acas!=cas: raise RuntimeError("commit authorization CAS binding mismatch")
    return a

def evaluate_manifest(m:dict)->dict:
    proto=load(PROTO); exact_keys(m,MANIFEST_KEYS,"commit authorization ceremony manifest")
    hits=forbidden_keys(m,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("ceremony manifest contains prohibited field: "+hits[0])
    if m["mode"]!="SYNTHETIC" or m["synthetic_fixture"] is not True: raise RuntimeError("commit authorization ceremony is synthetic-only")
    cid=str(m["ceremony_id"])
    if not CEREMONY_RE.fullmatch(cid): raise RuntimeError("synthetic ceremony_id invalid")
    evaluation=parse_time(m["evaluation_at_utc"],"evaluation_at_utc")
    review=validate_review_receipt(m,proto,evaluation)
    changeset=validate_changeset(m,review,proto)
    decision=validate_decision(m,review,changeset)
    cas=current_cas(changeset)
    auth=validate_authorization(m,review,changeset,decision,cas,proto,evaluation)
    return {
      "version":"1.0","artifact_class":proto["output_contract"]["artifact_class"],"storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,"mode":"SYNTHETIC","status":proto["output_contract"]["status"],
      "ceremony_id":cid,"evaluation_at_utc":m["evaluation_at_utc"],"authorization_id":auth["authorization_id"],
      "authorizer_ref_sha256":hashlib.sha256(("commit-authorizer:"+auth["authorizer_reference"]).encode()).hexdigest(),
      "review_batch_id":review["review_batch_id"],"review_receipt_sha256":m["review_receipt_sha256"],
      "prepare_id":changeset["prepare_id"],"changeset_sha256":m["changeset_sha256"],
      "decision_id":decision["decision_id"],"decision_record_sha256":m["decision_record_sha256"],
      "requested_combination_id":changeset["requested_combination_id"],
      "requested_market_data_candidate_id":changeset["requested_market_data_candidate_id"],
      "requested_kms_candidate_id":changeset["requested_kms_candidate_id"],
      "lifecycle_event_count":changeset["lifecycle_event_count"],"lifecycle_head_sha256":changeset["lifecycle_head_sha256"],
      "production_state_cas_sha256":cas,"review_freshness_revalidated":True,"cas_revalidated_at_ceremony":True,
      "authorization_status":"SYNTHETIC_DISABLED","commit_authorized":False,"apply_authorized":False,"execution_capability":False,
      "selection_transition_permitted":False,"selection_written":False,"selected_market_data_provider":"UNSELECTED",
      "selected_key_custody_provider":"UNSELECTED","selected_combination_id":"UNSELECTED","production_state_mutated":False,
      "credentials_connected":False,"kms_api_called":False,"key_created":False,"real_activation_manifest_generated":False,"real_activation_authorized":False
    }

def process(manifest_path:Path,ceremony_store_root:Path)->dict:
    require_external(manifest_path,"commit authorization ceremony manifest");require_external(ceremony_store_root,"commit authorization ceremony store")
    if not manifest_path.is_file(): raise RuntimeError("commit authorization ceremony manifest missing")
    receipt=evaluate_manifest(load(manifest_path))
    target=ceremony_store_root.resolve()/"commit_authorization_ceremonies"/(receipt["ceremony_id"]+".json")
    result=write_immutable_json(ceremony_store_root.resolve(),target,receipt)
    return {"status":"SYNTHETIC_COMMIT_AUTHORIZATION_CEREMONY_RECORDED" if result["status"]=="WRITTEN" else "IDEMPOTENT_REPLAY_ACCEPTED",
      "ceremony_id":receipt["ceremony_id"],"ceremony_receipt_sha256":result["sha256"],"commit_authorized":False,"apply_authorized":False,
      "execution_capability":False,"selection_written":False,"production_state_mutated":False,"real_activation_authorized":False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--manifest",type=Path,required=True);ap.add_argument("--ceremony-store-root",type=Path,required=True);a=ap.parse_args()
    print(json.dumps(process(a.manifest,a.ceremony_store_root),indent=2))
if __name__=="__main__":main()
