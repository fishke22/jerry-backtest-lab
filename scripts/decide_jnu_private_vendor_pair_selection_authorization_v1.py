from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external, write_immutable_json

ROOT=Path(__file__).resolve().parents[1]
PROTO=ROOT/"config"/"jnu_private_vendor_pair_selection_authorization_protocol_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"

REQUEST_KEYS={"version","mode","synthetic_fixture","decision_id","decision_at_utc","requested_combination_id","review_receipt_path","review_receipt_sha256","authorization_path","authorization_sha256"}
AUTH_KEYS={"version","artifact_class","mode","synthetic_fixture","authorization_id","authorization_scope","authorization_status","authorizer_role","authorizer_reference","authorizer_attestation","review_batch_id","review_receipt_sha256","composite_dossier_sha256","authorized_combination_id","issued_at_utc","valid_from_utc","expires_at_utc","selection_write_permitted","real_selection_authorized"}
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

def parse_time(value,label:str)->datetime:
    try:d=datetime.fromisoformat(str(value))
    except Exception as e: raise RuntimeError(label+" invalid") from e
    if d.tzinfo is None: raise RuntimeError(label+" must be timezone-aware")
    return d

def expected_combinations(shortlist:dict)->set[str]:
    return {p["id"]+"__"+k["id"] for p in shortlist["market_data_candidates"] for k in shortlist["key_custody_candidates"]}

def validate_production_state(shortlist:dict,key:dict,terms:dict,proto:dict)->None:
    g=proto["production_state_gate"]
    if shortlist.get("selected_market_data_provider")!=g["shortlist_selected_market_data_provider_must_equal"]:
        raise RuntimeError("market-data provider production state already selected/mutated")
    if shortlist.get("selected_key_custody_provider")!=g["shortlist_selected_key_custody_provider_must_equal"]:
        raise RuntimeError("KMS provider production state already selected/mutated")
    if key.get("production_enabled") is not g["production_key_enabled_must_equal"]:
        raise RuntimeError("production key enabled state mutated")
    if key.get("vendor")!=g["production_key_vendor_must_equal"] or key.get("region")!=g["production_key_region_must_equal"]:
        raise RuntimeError("production key vendor/region state mutated")
    if terms.get("broker_auth_used") is not g["broker_auth_used_must_equal"]:
        raise RuntimeError("broker auth state violates selection gate")
    if terms.get("trading_permission_used") is not g["trading_permission_used_must_equal"]:
        raise RuntimeError("trading permission state violates selection gate")
    if terms.get("public_output_requested") is not g["public_output_requested_must_equal"]:
        raise RuntimeError("public output state violates selection gate")

def validate_receipt(path:Path,expected_sha:str,decision_at:datetime,proto:dict,shortlist:dict)->dict:
    if not path.is_absolute(): raise RuntimeError("review_receipt_path must be absolute")
    require_external(path,"dual-control review receipt")
    if not path.is_file(): raise RuntimeError("dual-control review receipt missing")
    if not HEX64.fullmatch(expected_sha): raise RuntimeError("review_receipt_sha256 invalid")
    actual=sha256_file(path)
    if actual!=expected_sha: raise RuntimeError("dual-control review receipt SHA-256 mismatch")
    x=load(path);c=proto["receipt_contract"]
    if x.get("artifact_class")!=c["artifact_class"] or x.get("storage_scope")!=c["storage_scope"] or x.get("mode")!=c["mode"]:
        raise RuntimeError("dual-control receipt artifact contract mismatch")
    for key in ["public_distribution_permitted","reviewer_ids_emitted","ranking_generated","recommendation_generated","selection_generated","market_data_provider_selected","kms_provider_selected","real_activation_authorized"]:
        if x.get(key) is not c[key]: raise RuntimeError("dual-control receipt boundary mismatch: "+key)
    if int(x.get("combination_count",-1))!=int(c["exact_combination_count"]) or int(x.get("review_count",-1))!=int(c["exact_review_count"]):
        raise RuntimeError("dual-control receipt coverage count mismatch")
    hits=forbidden_keys(x,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("dual-control receipt contains prohibited field: "+hits[0])
    receipt_eval=parse_time(x.get("evaluation_at_utc"),"receipt evaluation_at_utc")
    if decision_at < receipt_eval: raise RuntimeError("decision time precedes receipt evaluation")
    results=x.get("results")
    if not isinstance(results,list) or len(results)!=int(c["exact_combination_count"]): raise RuntimeError("dual-control receipt results invalid")
    by={};seen_reviews=set()
    for row in results:
        if not isinstance(row,dict): raise RuntimeError("dual-control result invalid")
        cid=row.get("combination_id")
        if not isinstance(cid,str) or cid in by: raise RuntimeError("duplicate/invalid receipt combination_id")
        if row.get("selected") is not False or row.get("real_activation_authorized") is not False:
            raise RuntimeError("dual-control result indicates forbidden selection/activation")
        reviews=row.get("reviews")
        if not isinstance(reviews,list) or len(reviews)!=2: raise RuntimeError("each receipt result requires two reviews")
        roles=set()
        for r in reviews:
            rid=str(r.get("review_id",""))
            if not rid or rid in seen_reviews: raise RuntimeError("duplicate/invalid receipt review_id")
            seen_reviews.add(rid)
            roles.add(r.get("reviewer_role"))
            ref=str(r.get("reviewer_ref_sha256",""))
            if not HEX64.fullmatch(ref): raise RuntimeError("reviewer reference SHA invalid")
            reval=parse_time(r.get("revalidation_due_at_utc"),"review revalidation_due_at_utc")
            expiry=parse_time(r.get("expires_at_utc"),"review expires_at_utc")
            if decision_at>=reval or decision_at>expiry: raise RuntimeError("dual-control review receipt stale or expired at decision time")
        if roles!=set(c["exact_roles"]): raise RuntimeError("receipt reviewer roles mismatch")
        by[cid]=row
    if set(by)!=expected_combinations(shortlist): raise RuntimeError("dual-control receipt does not cover exact six-pair shortlist")
    return {"receipt":x,"by":by,"sha256":actual}

def validate_authorization(path:Path,expected_sha:str,request:dict,receipt:dict,decision_at:datetime,proto:dict)->dict:
    if not path.is_absolute(): raise RuntimeError("authorization_path must be absolute")
    require_external(path,"selection authorization artifact")
    if not path.is_file(): raise RuntimeError("selection authorization artifact missing")
    if not HEX64.fullmatch(expected_sha): raise RuntimeError("authorization_sha256 invalid")
    actual=sha256_file(path)
    if actual!=expected_sha: raise RuntimeError("selection authorization artifact SHA-256 mismatch")
    a=load(path);exact_keys(a,AUTH_KEYS,"selection authorization artifact")
    hits=forbidden_keys(a,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("selection authorization contains prohibited field: "+hits[0])
    c=proto["authorization_contract"]
    if a.get("artifact_class")!=c["artifact_class"] or a.get("mode")!="SYNTHETIC" or a.get("synthetic_fixture") is not True:
        raise RuntimeError("selection authorization artifact contract mismatch")
    for k in ["authorization_scope","authorization_status","authorizer_role","authorizer_attestation","selection_write_permitted","real_selection_authorized"]:
        if a.get(k)!=c[k]: raise RuntimeError("selection authorization frozen value mismatch: "+k)
    auth_ref=str(a.get("authorizer_reference",""))
    if not auth_ref: raise RuntimeError("authorizer_reference required")
    issued=parse_time(a.get("issued_at_utc"),"authorization issued_at_utc")
    valid_from=parse_time(a.get("valid_from_utc"),"authorization valid_from_utc")
    expires=parse_time(a.get("expires_at_utc"),"authorization expires_at_utc")
    if issued>valid_from or valid_from>decision_at or decision_at>=expires:
        raise RuntimeError("selection authorization is not current at decision time")
    if a.get("review_receipt_sha256")!=receipt["sha256"]: raise RuntimeError("authorization receipt SHA binding mismatch")
    if a.get("review_batch_id")!=receipt["receipt"].get("review_batch_id"): raise RuntimeError("authorization review_batch_id binding mismatch")
    if a.get("composite_dossier_sha256")!=receipt["receipt"].get("composite_dossier_sha256"): raise RuntimeError("authorization composite dossier SHA binding mismatch")
    if a.get("authorized_combination_id")!=request["requested_combination_id"]:
        raise RuntimeError("requested vendor pair does not match explicit authorization")
    return {"authorization":a,"sha256":actual,"authorizer_reference":auth_ref}

def evaluate_request(request:dict)->dict:
    proto=load(PROTO);shortlist=load(SHORTLIST);key=load(KEY_CURRENT);terms=load(TERMS_CURRENT)
    exact_keys(request,REQUEST_KEYS,"selection decision request")
    hits=forbidden_keys(request,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("selection decision request contains prohibited field: "+hits[0])
    if request.get("mode")!="SYNTHETIC" or request.get("synthetic_fixture") is not True:
        raise RuntimeError("selection authorization decision gate is synthetic-only")
    did=str(request.get("decision_id",""))
    if not did.startswith(proto["request_contract"]["decision_id_prefix"]) or len(did)<=len(proto["request_contract"]["decision_id_prefix"]):
        raise RuntimeError("synthetic decision_id invalid")
    decision_at=parse_time(request.get("decision_at_utc"),"decision_at_utc")
    validate_production_state(shortlist,key,terms,proto)
    combos=expected_combinations(shortlist)
    requested=str(request.get("requested_combination_id",""))
    if requested not in combos: raise RuntimeError("requested vendor pair is not in frozen shortlist")
    receipt=validate_receipt(Path(str(request.get("review_receipt_path"))),str(request.get("review_receipt_sha256","")),decision_at,proto,shortlist)
    target=receipt["by"][requested]
    if target.get("outcome")!=proto["receipt_contract"]["approved_outcome"] or target.get("underlying_synthetic_evidence_complete") is not True:
        raise RuntimeError("requested vendor pair lacks current dual-control synthetic approval")
    auth=validate_authorization(Path(str(request.get("authorization_path"))),str(request.get("authorization_sha256","")),request,receipt,decision_at,proto)
    p,k=requested.split("__",1)
    return {
      "version":"1.0",
      "artifact_class":"JNU_SYNTHETIC_VENDOR_PAIR_SELECTION_DECISION_RECORD",
      "storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,
      "mode":"SYNTHETIC",
      "status":proto["decision_output"]["status"],
      "decision_id":did,
      "decision_at_utc":request["decision_at_utc"],
      "requested_combination_id":requested,
      "requested_market_data_candidate_id":p,
      "requested_kms_candidate_id":k,
      "review_batch_id":receipt["receipt"].get("review_batch_id"),
      "review_receipt_sha256":receipt["sha256"],
      "composite_dossier_sha256":receipt["receipt"].get("composite_dossier_sha256"),
      "authorization_id":auth["authorization"].get("authorization_id"),
      "authorization_sha256":auth["sha256"],
      "authorizer_ref_sha256":hashlib.sha256(("authorizer:"+auth["authorizer_reference"]).encode()).hexdigest(),
      "authorization_status":auth["authorization"].get("authorization_status"),
      "authorization_binding_validated":True,
      "dual_control_approval_validated":True,
      "exact_six_pair_coverage_validated":True,
      "selected_market_data_provider":"UNSELECTED",
      "selected_key_custody_provider":"UNSELECTED",
      "selected_combination_id":"UNSELECTED",
      "selection_transition_permitted":False,
      "selection_written":False,
      "production_state_mutated":False,
      "credentials_connected":False,
      "kms_api_called":False,
      "key_created":False,
      "real_activation_manifest_generated":False,
      "real_activation_authorized":False
    }

def process(request_path:Path,decision_store_root:Path)->dict:
    require_external(request_path,"selection decision request")
    require_external(decision_store_root,"selection decision store")
    if not request_path.is_file(): raise RuntimeError("selection decision request missing")
    request=load(request_path)
    decision=evaluate_request(request)
    hits=forbidden_keys(decision,set(load(PROTO)["prohibited_keys"]))
    if hits: raise RuntimeError("selection decision record contains prohibited field: "+hits[0])
    target=decision_store_root.resolve()/"selection_decisions"/(decision["decision_id"]+".json")
    result=write_immutable_json(decision_store_root.resolve(),target,decision)
    return {
      "status":"SYNTHETIC_SELECTION_DECISION_RECORDED" if result["status"]=="WRITTEN" else "IDEMPOTENT_REPLAY_ACCEPTED",
      "decision_id":decision["decision_id"],
      "decision_record_sha256":result["sha256"],
      "selection_transition_permitted":False,
      "selection_written":False,
      "selected_combination_id":"UNSELECTED",
      "real_activation_authorized":False
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--request",type=Path,required=True)
    ap.add_argument("--decision-store-root",type=Path,required=True)
    a=ap.parse_args()
    print(json.dumps(process(a.request,a.decision_store_root),indent=2))

if __name__=="__main__": main()
