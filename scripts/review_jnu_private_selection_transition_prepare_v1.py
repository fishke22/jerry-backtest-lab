from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external, write_immutable_json, verify_backup, sha256_file

ROOT=Path(__file__).resolve().parents[1]
PROTO=ROOT/"config"/"jnu_private_selection_transition_prepare_review_protocol_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"

TOP_KEYS={
  "version","mode","synthetic_fixture","review_batch_id","evaluation_at_utc",
  "prepare_store_root","changeset_path","changeset_sha256",
  "decision_store_root","decision_record_path","decision_record_sha256","reviews"
}
REVIEW_KEYS={
  "review_id","reviewer_role","reviewer_id","disposition",
  "changeset_sha256","decision_record_sha256","requested_combination_id",
  "reviewed_at_utc","revalidation_due_at_utc","expires_at_utc","reviewer_attestation"
}
HEX64=re.compile(r"^[0-9a-f]{64}$")
BATCH_RE=re.compile(r"^JNU_PREPARE_REVIEW_SYNTH_[A-Za-z0-9_-]+$")

def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise RuntimeError(f"{p} must contain an object")
    return x

def exact_keys(x:dict,allowed:set[str],label:str)->None:
    extra=set(x)-allowed
    missing=allowed-set(x)
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
    require_external(root,label+" store"); require_external(path,label)
    if not root.is_absolute() or not path.is_absolute(): raise RuntimeError(label+" store/path must be absolute")
    root=root.resolve();path=path.resolve()
    if path.parent!=(root/subdir).resolve(): raise RuntimeError(label+" must be inside canonical store subdirectory")
    if not path.is_file(): raise RuntimeError(label+" missing")
    if not HEX64.fullmatch(expected_sha): raise RuntimeError(label+" SHA-256 invalid")
    if sha256_file(path)!=expected_sha: raise RuntimeError(label+" SHA-256 mismatch")
    if verify_backup(root,path).get("status")!="PASS": raise RuntimeError(label+" immutable backup/checksum invalid")
    return load(path)

def validate_changeset(manifest:dict,proto:dict)->dict:
    root=Path(str(manifest["prepare_store_root"]))
    path=Path(str(manifest["changeset_path"]))
    sha=str(manifest["changeset_sha256"])
    c=validate_external_record(root,path,sha,"selection_transition_prepares","PREPARE changeset")
    cc=proto["changeset_contract"]
    for k in ["artifact_class","status","storage_scope","public_distribution_permitted","mode","operation","commit_capability","apply_capability","selection_transition_permitted","selection_written","selected_combination_id","production_state_mutated","real_activation_authorized"]:
        if c.get(k)!=cc[k]: raise RuntimeError("PREPARE changeset contract mismatch: "+k)
    if c.get("compare_and_swap_required") is not True: raise RuntimeError("PREPARE changeset must require compare-and-swap")
    hits=forbidden_keys(c,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("PREPARE changeset contains prohibited field: "+hits[0])
    return {"record":c,"sha256":sha}

def validate_decision(manifest:dict,changeset:dict,proto:dict)->dict:
    root=Path(str(manifest["decision_store_root"]))
    path=Path(str(manifest["decision_record_path"]))
    sha=str(manifest["decision_record_sha256"])
    d=validate_external_record(root,path,sha,"selection_lifecycle_decisions","lifecycle-integrated decision")
    dc=proto["decision_lineage_contract"]
    for k in ["artifact_class","status","storage_scope","public_distribution_permitted","mode","selection_transition_permitted","selection_written","selected_combination_id","production_state_mutated","real_activation_authorized","lifecycle_full_chain_validated","lifecycle_event_backups_validated","lifecycle_current_authorization_validated"]:
        if d.get(k)!=dc[k]: raise RuntimeError("decision lineage contract mismatch: "+k)
    c=changeset["record"]
    if c.get("decision_id")!=d.get("decision_id") or c.get("decision_record_sha256")!=sha:
        raise RuntimeError("PREPARE changeset decision lineage mismatch")
    for k in ["requested_combination_id","requested_market_data_candidate_id","requested_kms_candidate_id","lifecycle_event_count","lifecycle_head_sha256"]:
        if c.get(k)!=d.get(k): raise RuntimeError("PREPARE/decision lineage mismatch: "+k)
    hits=forbidden_keys(d,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("decision record contains prohibited field: "+hits[0])
    return {"record":d,"sha256":sha}

def recheck_cas(changeset:dict,proto:dict)->tuple[bool,dict]:
    c=changeset["record"]
    snaps=c.get("production_state_preconditions")
    expected=set(proto["cas_revalidation"]["exact_snapshot_ids"])
    if not isinstance(snaps,dict) or set(snaps)!=expected: raise RuntimeError("PREPARE changeset CAS surface mismatch")
    paths={
      "PROVIDER_SELECTION_SHORTLIST":SHORTLIST,
      "PRODUCTION_KEY_CUSTODY_CURRENT":KEY_CURRENT,
      "PROVIDER_TERM_READINESS_CURRENT":TERMS_CURRENT
    }
    current={}
    fresh=True
    for sid,p in paths.items():
        row=snaps[sid]
        if not isinstance(row,dict) or row.get("path")!=str(p.relative_to(ROOT)):
            raise RuntimeError("PREPARE changeset CAS path mismatch: "+sid)
        expected_sha=str(row.get("sha256",""))
        if not HEX64.fullmatch(expected_sha): raise RuntimeError("PREPARE changeset CAS SHA invalid: "+sid)
        actual=sha256_file(p)
        current[sid]={"expected_sha256":expected_sha,"actual_sha256":actual,"fresh":actual==expected_sha}
        fresh=fresh and actual==expected_sha
    return fresh,current

def evaluate_manifest(manifest:dict)->dict:
    proto=load(PROTO)
    exact_keys(manifest,TOP_KEYS,"PREPARE dual-control review manifest")
    hits=forbidden_keys(manifest,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("review manifest contains prohibited field: "+hits[0])
    if manifest["mode"]!="SYNTHETIC" or manifest["synthetic_fixture"] is not True:
        raise RuntimeError("PREPARE dual-control review is synthetic-only")
    batch=str(manifest["review_batch_id"])
    if not BATCH_RE.fullmatch(batch): raise RuntimeError("synthetic review_batch_id invalid")
    evaluation=parse_time(manifest["evaluation_at_utc"],"evaluation_at_utc")

    changeset=validate_changeset(manifest,proto)
    decision=validate_decision(manifest,changeset,proto)
    c=changeset["record"]; pair=str(c.get("requested_combination_id",""))
    if pair!=str(c.get("requested_market_data_candidate_id",""))+"__"+str(c.get("requested_kms_candidate_id","")):
        raise RuntimeError("PREPARE changeset pair reconstruction mismatch")
    fresh_state,cas=recheck_cas(changeset,proto)

    reviews=manifest["reviews"]
    rc=proto["review_contract"]
    if not isinstance(reviews,list) or len(reviews)!=rc["exact_review_count"]: raise RuntimeError("exactly two reviews required")
    seen_ids=set();seen_roles=set();seen_reviewers=set();normalized=[]
    for r in reviews:
        if not isinstance(r,dict): raise RuntimeError("review must be object")
        exact_keys(r,REVIEW_KEYS,"PREPARE review")
        rid=str(r["review_id"]); role=r["reviewer_role"]; reviewer=str(r["reviewer_id"])
        if not rid or rid in seen_ids: raise RuntimeError("duplicate/invalid review_id")
        seen_ids.add(rid)
        if role not in rc["required_roles"] or role in seen_roles: raise RuntimeError("reviewer role missing/duplicate/invalid")
        seen_roles.add(role)
        if not reviewer or reviewer in seen_reviewers: raise RuntimeError("reviewer IDs must be independent")
        seen_reviewers.add(reviewer)
        disp=r["disposition"]
        if disp not in rc["allowed_dispositions"]: raise RuntimeError("invalid review disposition")
        if r["reviewer_attestation"]!=rc["reviewer_attestation_required"]: raise RuntimeError("reviewer attestation missing")
        if r["changeset_sha256"]!=changeset["sha256"]: raise RuntimeError("review changeset SHA binding mismatch")
        if r["decision_record_sha256"]!=decision["sha256"]: raise RuntimeError("review decision SHA binding mismatch")
        if r["requested_combination_id"]!=pair: raise RuntimeError("review pair binding mismatch")
        reviewed=parse_time(r["reviewed_at_utc"],"reviewed_at_utc")
        reval=parse_time(r["revalidation_due_at_utc"],"revalidation_due_at_utc")
        expiry=parse_time(r["expires_at_utc"],"expires_at_utc")
        if not (reviewed<reval<=expiry): raise RuntimeError("review/revalidation/expiry chronology invalid")
        if evaluation<reviewed: raise RuntimeError("evaluation precedes review")
        stale=evaluation>=reval or evaluation>expiry
        normalized.append({
          "review_id":rid,"reviewer_role":role,
          "reviewer_ref_sha256":hashlib.sha256(("reviewer:"+reviewer).encode()).hexdigest(),
          "disposition":disp,"reviewed_at_utc":r["reviewed_at_utc"],
          "revalidation_due_at_utc":r["revalidation_due_at_utc"],"expires_at_utc":r["expires_at_utc"],
          "reviewer_attestation":r["reviewer_attestation"],"_stale":stale
        })
    if seen_roles!=set(rc["required_roles"]): raise RuntimeError("both reviewer roles required")

    rules=proto["outcome_rules"]
    dispositions={r["disposition"] for r in normalized}
    if not fresh_state:
        outcome=rules["stale_production_state"]
    elif any(r["_stale"] for r in normalized):
        outcome=rules["stale_or_expired"]
    elif len(dispositions)>1:
        outcome=rules["conflict"]
    else:
        d=normalized[0]["disposition"]
        outcome=rules["dual_approve"] if d=="APPROVE" else rules["dual_reject"] if d=="REJECT" else rules["dual_needs_evidence"]

    safe_reviews=[{k:v for k,v in r.items() if not k.startswith("_")} for r in sorted(normalized,key=lambda x:x["reviewer_role"])]
    return {
      "version":"1.0",
      "artifact_class":proto["output_contract"]["artifact_class"],
      "storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,
      "mode":"SYNTHETIC",
      "review_batch_id":batch,
      "evaluation_at_utc":manifest["evaluation_at_utc"],
      "prepare_id":c["prepare_id"],
      "changeset_sha256":changeset["sha256"],
      "decision_id":decision["record"]["decision_id"],
      "decision_record_sha256":decision["sha256"],
      "lifecycle_event_count":c["lifecycle_event_count"],
      "lifecycle_head_sha256":c["lifecycle_head_sha256"],
      "requested_combination_id":pair,
      "requested_market_data_candidate_id":c["requested_market_data_candidate_id"],
      "requested_kms_candidate_id":c["requested_kms_candidate_id"],
      "cas_revalidated_at_review":True,
      "cas_state_fresh":fresh_state,
      "cas_revalidation":cas,
      "review_count":2,
      "reviews":safe_reviews,
      "reviewer_ids_emitted":False,
      "outcome":outcome,
      "commit_capability":False,
      "apply_capability":False,
      "selection_transition_permitted":False,
      "selection_written":False,
      "selected_market_data_provider":"UNSELECTED",
      "selected_key_custody_provider":"UNSELECTED",
      "selected_combination_id":"UNSELECTED",
      "production_state_mutated":False,
      "real_activation_authorized":False
    }

def process(manifest_path:Path,review_store_root:Path)->dict:
    require_external(manifest_path,"PREPARE dual-control review manifest")
    require_external(review_store_root,"PREPARE dual-control review store")
    if not manifest_path.is_file(): raise RuntimeError("PREPARE dual-control review manifest missing")
    manifest=load(manifest_path)
    receipt=evaluate_manifest(manifest)
    hits=forbidden_keys(receipt,set(load(PROTO)["prohibited_keys"]))
    if hits: raise RuntimeError("redacted review receipt contains prohibited field: "+hits[0])
    target=review_store_root.resolve()/"prepare_review_receipts"/(receipt["review_batch_id"]+".json")
    result=write_immutable_json(review_store_root.resolve(),target,receipt)
    return {
      "status":"SYNTHETIC_PREPARE_DUAL_CONTROL_REVIEW_RECORDED" if result["status"]=="WRITTEN" else "IDEMPOTENT_REPLAY_ACCEPTED",
      "review_batch_id":receipt["review_batch_id"],
      "review_receipt_sha256":result["sha256"],
      "outcome":receipt["outcome"],
      "commit_capability":False,
      "apply_capability":False,
      "selection_written":False,
      "production_state_mutated":False,
      "real_activation_authorized":False
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--review-store-root",type=Path,required=True)
    a=ap.parse_args()
    print(json.dumps(process(a.manifest,a.review_store_root),indent=2))

if __name__=="__main__":main()
