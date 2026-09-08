from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external, write_immutable_json

ROOT=Path(__file__).resolve().parents[1]
PROTO=ROOT/"config"/"jnu_private_composite_evidence_review_dual_control_protocol_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"

TOP_KEYS={"version","mode","synthetic_fixture","review_batch_id","evaluation_at_utc","composite_dossier_path","composite_dossier_sha256","reviews"}
REVIEW_KEYS={"review_id","combination_id","reviewer_role","reviewer_id","disposition","dossier_sha256","reviewed_at_utc","revalidation_due_at_utc","expires_at_utc","reviewer_attestation"}
BATCH_RE=re.compile(r"^JNU_REVIEW_SYNTH_[A-Za-z0-9_-]+$")
HEX64=re.compile(r"^[0-9a-f]{64}$")

def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise RuntimeError(f"{p} must contain an object")
    return x

def sha256_file(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def canonical_sha256(obj)->str:
    raw=json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

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

def parse_time(s:str,label:str)->datetime:
    try:d=datetime.fromisoformat(str(s))
    except Exception as e: raise RuntimeError(label+" invalid") from e
    if d.tzinfo is None: raise RuntimeError(label+" must be timezone-aware")
    return d

def expected_combinations()->set[str]:
    s=load(SHORTLIST)
    return {p["id"]+"__"+k["id"] for p in s["market_data_candidates"] for k in s["key_custody_candidates"]}

def validate_composite(path:Path,expected_sha:str,proto:dict)->tuple[dict,dict[str,dict],str]:
    if not path.is_absolute(): raise RuntimeError("composite_dossier_path must be absolute")
    require_external(path,"composite dossier")
    if not path.is_file(): raise RuntimeError("composite dossier missing")
    actual=sha256_file(path)
    if actual!=expected_sha: raise RuntimeError("composite dossier SHA-256 mismatch")
    x=load(path)
    if x.get("artifact_class")!="JNU_PRIVATE_COMPOSITE_PREACTIVATION_READINESS_DOSSIERS" or x.get("storage_scope")!="PRIVATE_INTERNAL_ONLY" or x.get("mode")!="SYNTHETIC":
        raise RuntimeError("composite dossier artifact contract mismatch")
    if x.get("public_distribution_permitted") is not False or x.get("real_activation_authorized") is not False:
        raise RuntimeError("composite dossier violates private/nonactivation boundary")
    if x.get("ranking_generated") is not False or x.get("recommendation_generated") is not False or x.get("selection_generated") is not False:
        raise RuntimeError("composite dossier contains forbidden ranking/recommendation/selection")
    if x.get("market_data_provider_selected") is not False or x.get("kms_provider_selected") is not False:
        raise RuntimeError("composite dossier indicates provider selection")
    hits=forbidden_keys(x,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("composite dossier contains prohibited field: "+hits[0])
    ds=x.get("dossiers")
    if not isinstance(ds,list) or len(ds)!=int(proto["review_contract"]["exact_combination_count"]): raise RuntimeError("composite dossier must contain exactly six dossiers")
    by={}
    for d in ds:
        cid=d.get("combination_id")
        if not isinstance(cid,str) or cid in by: raise RuntimeError("duplicate/invalid composite combination_id")
        if d.get("rank") is not None or d.get("recommended") is not False or d.get("selected") is not False or d.get("real_activation_authorized") is not False:
            raise RuntimeError("individual dossier violates no-ranking/no-selection boundary")
        by[cid]=d
    if set(by)!=expected_combinations(): raise RuntimeError("composite dossier combination set does not match shortlist")
    return x,by,actual

def evaluate_manifest(manifest:dict)->dict:
    proto=load(PROTO)
    exact_keys(manifest,TOP_KEYS,"dual-control review manifest")
    hits=forbidden_keys(manifest,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("review manifest contains prohibited field: "+hits[0])
    if manifest.get("mode")!="SYNTHETIC" or manifest.get("synthetic_fixture") is not True:
        raise RuntimeError("dual-control review is synthetic-only")
    batch=str(manifest.get("review_batch_id",""))
    if not BATCH_RE.fullmatch(batch): raise RuntimeError("synthetic review_batch_id invalid")
    evaluation=parse_time(manifest.get("evaluation_at_utc"),"evaluation_at_utc")
    composite_path=Path(str(manifest.get("composite_dossier_path")))
    expected_sha=str(manifest.get("composite_dossier_sha256",""))
    if not HEX64.fullmatch(expected_sha): raise RuntimeError("composite_dossier_sha256 invalid")
    composite,by,actual=validate_composite(composite_path,expected_sha,proto)

    reviews=manifest.get("reviews")
    if not isinstance(reviews,list) or len(reviews)!=int(proto["review_contract"]["exact_total_review_count"]):
        raise RuntimeError("exactly twelve reviews required")
    seen_review_ids=set()
    grouped={cid:[] for cid in by}
    for r in reviews:
        if not isinstance(r,dict): raise RuntimeError("review must be object")
        exact_keys(r,REVIEW_KEYS,"review")
        rid=str(r.get("review_id",""))
        if not rid or rid in seen_review_ids: raise RuntimeError("duplicate/invalid review_id")
        seen_review_ids.add(rid)
        cid=str(r.get("combination_id",""))
        if cid not in grouped: raise RuntimeError("review targets unknown combination")
        role=r.get("reviewer_role")
        if role not in proto["review_contract"]["required_roles"]: raise RuntimeError("invalid reviewer_role")
        reviewer_id=str(r.get("reviewer_id",""))
        if not reviewer_id: raise RuntimeError("reviewer_id required")
        disposition=r.get("disposition")
        if disposition not in proto["review_contract"]["allowed_dispositions"]: raise RuntimeError("invalid review disposition")
        if r.get("reviewer_attestation")!=proto["review_contract"]["reviewer_attestation_required"]: raise RuntimeError("reviewer attestation missing")
        dsha=str(r.get("dossier_sha256",""))
        if not HEX64.fullmatch(dsha) or dsha!=canonical_sha256(by[cid]): raise RuntimeError("review dossier SHA-256 binding mismatch")
        reviewed=parse_time(r.get("reviewed_at_utc"),"reviewed_at_utc")
        reval=parse_time(r.get("revalidation_due_at_utc"),"revalidation_due_at_utc")
        expiry=parse_time(r.get("expires_at_utc"),"expires_at_utc")
        if not (reviewed < reval <= expiry): raise RuntimeError("review/revalidation/expiry chronology invalid")
        if evaluation < reviewed: raise RuntimeError("evaluation_at_utc precedes review")
        grouped[cid].append({
          "review_id":rid,"role":role,"reviewer_id":reviewer_id,"disposition":disposition,
          "reviewed_at_utc":r["reviewed_at_utc"],"revalidation_due_at_utc":r["revalidation_due_at_utc"],"expires_at_utc":r["expires_at_utc"],
          "reviewer_attestation":r["reviewer_attestation"],"dossier_sha256":dsha,
          "_reviewed":reviewed,"_reval":reval,"_expiry":expiry
        })

    receipt_rows=[]
    invariant=list(proto["invariant_activation_blockers"])
    for cid,d in by.items():
        rs=grouped[cid]
        if len(rs)!=int(proto["review_contract"]["exact_reviews_per_combination"]): raise RuntimeError("each combination requires exactly two reviews")
        roles={r["role"] for r in rs}
        if roles!=set(proto["review_contract"]["required_roles"]): raise RuntimeError("each combination requires both independent reviewer roles")
        if len({r["reviewer_id"] for r in rs})!=2: raise RuntimeError("reviewer IDs must be independent for each combination")
        dispositions={r["disposition"] for r in rs}
        stale=any(evaluation>=r["_reval"] or evaluation>r["_expiry"] for r in rs)
        if stale:
            status=proto["outcome_rules"]["revalidation_status"]
        elif len(dispositions)>1:
            status=proto["outcome_rules"]["conflict_status"]
        else:
            disposition=rs[0]["disposition"]
            if disposition=="REJECT": status=proto["outcome_rules"]["reject_status"]
            elif disposition=="NEEDS_EVIDENCE": status=proto["outcome_rules"]["needs_evidence_status"]
            elif not d.get("synthetic_evidence_complete",False): status=proto["outcome_rules"]["underlying_blocked_status"]
            else: status=proto["outcome_rules"]["approve_status"]
        receipt_rows.append({
          "combination_id":cid,
          "dossier_sha256":canonical_sha256(d),
          "outcome":status,
          "underlying_synthetic_evidence_complete":d.get("synthetic_evidence_complete") is True,
          "reviews":[{
            "review_id":r["review_id"],
            "reviewer_role":r["role"],
            "reviewer_ref_sha256":hashlib.sha256(("reviewer:"+r["reviewer_id"]).encode()).hexdigest(),
            "disposition":r["disposition"],
            "reviewed_at_utc":r["reviewed_at_utc"],
            "revalidation_due_at_utc":r["revalidation_due_at_utc"],
            "expires_at_utc":r["expires_at_utc"],
            "reviewer_attestation":r["reviewer_attestation"]
          } for r in sorted(rs,key=lambda z:z["role"])],
          "activation_blockers":invariant,
          "selected":False,
          "real_activation_authorized":False
        })

    key=load(KEY_CURRENT);terms=load(TERMS_CURRENT)
    return {
      "version":"1.0",
      "artifact_class":"JNU_REDACTED_SYNTHETIC_DUAL_CONTROL_REVIEW_RECEIPT",
      "storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,
      "mode":"SYNTHETIC",
      "review_batch_id":batch,
      "evaluation_at_utc":manifest["evaluation_at_utc"],
      "composite_dossier_sha256":actual,
      "combination_count":len(receipt_rows),
      "review_count":len(reviews),
      "results":receipt_rows,
      "reviewer_ids_emitted":False,
      "ranking_generated":False,
      "recommendation_generated":False,
      "selection_generated":False,
      "market_data_provider_selected":False,
      "kms_provider_selected":False,
      "production_key_profile_enabled":key.get("production_enabled") is True,
      "real_provider_terms_ready":not any(v=="UNRESOLVED" for k,v in terms.items() if k.endswith("_status")),
      "credentials_connected":False,
      "real_activation_manifest_generated":False,
      "real_activation_authorized":False
    }

def process(manifest_path:Path,review_store_root:Path)->dict:
    require_external(manifest_path,"dual-control review manifest")
    require_external(review_store_root,"dual-control review store")
    if not manifest_path.is_file(): raise RuntimeError("dual-control review manifest missing")
    manifest=load(manifest_path)
    receipt=evaluate_manifest(manifest)
    hits=forbidden_keys(receipt,set(load(PROTO)["prohibited_keys"]))
    if hits: raise RuntimeError("redacted dual-control receipt contains prohibited field: "+hits[0])
    target=review_store_root.resolve()/"review_receipts"/(receipt["review_batch_id"]+".json")
    result=write_immutable_json(review_store_root.resolve(),target,receipt)
    status="DUAL_CONTROL_RECEIPT_WRITTEN" if result["status"]=="WRITTEN" else "IDEMPOTENT_REPLAY_ACCEPTED"
    return {
      "status":status,
      "receipt_sha256":result["sha256"],
      "review_batch_id":receipt["review_batch_id"],
      "combination_count":receipt["combination_count"],
      "review_count":receipt["review_count"],
      "reviewer_ids_emitted":False,
      "selection_generated":False,
      "real_activation_authorized":False
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--review-store-root",type=Path,required=True)
    a=ap.parse_args()
    print(json.dumps(process(a.manifest,a.review_store_root),indent=2))

if __name__=="__main__": main()
