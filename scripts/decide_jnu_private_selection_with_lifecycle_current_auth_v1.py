from __future__ import annotations
import argparse, json, re
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external, write_immutable_json, verify_backup
from decide_jnu_private_vendor_pair_selection_authorization_v1 import (
    evaluate_request as evaluate_base_request,
    load, parse_time, sha256_file
)
from manage_jnu_private_vendor_pair_authorization_lifecycle_v1 import (
    audit_chain, event_files, validate_current_authorization
)

ROOT=Path(__file__).resolve().parents[1]
PROTO=ROOT/"config"/"jnu_private_selection_decision_lifecycle_integration_protocol_v1.json"
REQUEST_KEYS={
    "version","mode","synthetic_fixture","decision_id","decision_at_utc","requested_combination_id",
    "review_receipt_path","review_receipt_sha256","authorization_path","authorization_sha256",
    "lifecycle_store_root","lifecycle_expected_event_count","lifecycle_expected_head_sha256"
}
HEX64=re.compile(r"^[0-9a-f]{64}$")

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

def base_request(request:dict)->dict:
    return {
      "version":request["version"],
      "mode":request["mode"],
      "synthetic_fixture":request["synthetic_fixture"],
      "decision_id":request["decision_id"],
      "decision_at_utc":request["decision_at_utc"],
      "requested_combination_id":request["requested_combination_id"],
      "review_receipt_path":request["review_receipt_path"],
      "review_receipt_sha256":request["review_receipt_sha256"],
      "authorization_path":request["authorization_path"],
      "authorization_sha256":request["authorization_sha256"]
    }

def verify_lifecycle(store_root:Path,request:dict,authorization_id:str,authorization_sha256:str)->dict:
    proto=load(PROTO)
    require_external(store_root,"authorization lifecycle store")
    decision_at=parse_time(request["decision_at_utc"],"decision_at_utc")
    expected_count=request.get("lifecycle_expected_event_count")
    if not isinstance(expected_count,int) or expected_count<1:
        raise RuntimeError("lifecycle_expected_event_count must be integer >= 1")
    expected_head=str(request.get("lifecycle_expected_head_sha256",""))
    if not HEX64.fullmatch(expected_head):
        raise RuntimeError("lifecycle_expected_head_sha256 invalid")

    files=event_files(store_root)
    if not files:
        raise RuntimeError("authorization lifecycle is missing")
    for p in files:
        b=verify_backup(store_root.resolve(),p.resolve())
        if b.get("status")!="PASS":
            raise RuntimeError("authorization lifecycle event backup/checksum verification failed")
        e=load(p)
        if parse_time(e.get("event_at_utc"),"lifecycle event_at_utc")>decision_at:
            raise RuntimeError("authorization lifecycle contains event after decision time")

    state=audit_chain(store_root,decision_at)
    if state.get("event_count")!=expected_count:
        raise RuntimeError("authorization lifecycle event-count binding mismatch")
    if state.get("last_event_sha256")!=expected_head:
        raise RuntimeError("authorization lifecycle head SHA-256 binding mismatch")

    current=validate_current_authorization(
        store_root,authorization_id,authorization_sha256,request["decision_at_utc"]
    )
    if current.get("authorized_combination_id")!=request["requested_combination_id"]:
        raise RuntimeError("lifecycle current authorization pair does not match requested pair")
    return {
      "event_count":state["event_count"],
      "head_sha256":state["last_event_sha256"],
      "current_status":state["current_status"],
      "authorization_id":authorization_id,
      "authorization_sha256":authorization_sha256,
      "authorized_combination_id":current["authorized_combination_id"]
    }

def evaluate_request(request:dict)->dict:
    proto=load(PROTO)
    exact_keys(request,REQUEST_KEYS,"lifecycle-integrated selection decision request")
    hits=forbidden_keys(request,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("integrated selection request contains prohibited field: "+hits[0])
    if request.get("mode")!=proto["request_contract"]["mode"] or request.get("synthetic_fixture") is not True:
        raise RuntimeError("lifecycle-integrated selection decision is synthetic-only")
    did=str(request.get("decision_id",""))
    prefix=proto["request_contract"]["decision_id_prefix"]
    if not did.startswith(prefix) or len(did)<=len(prefix):
        raise RuntimeError("integrated synthetic decision_id invalid")

    base=evaluate_base_request(base_request(request))
    auth_id=str(base.get("authorization_id",""))
    auth_sha=str(base.get("authorization_sha256",""))
    if not auth_id or not HEX64.fullmatch(auth_sha):
        raise RuntimeError("base decision did not yield valid authorization identity")
    lifecycle=verify_lifecycle(Path(str(request.get("lifecycle_store_root"))),request,auth_id,auth_sha)

    if base.get("selection_transition_permitted") is not False or base.get("selection_written") is not False:
        raise RuntimeError("base selection gate unexpectedly permits selection")
    if base.get("selected_combination_id")!="UNSELECTED" or base.get("real_activation_authorized") is not False:
        raise RuntimeError("base selection gate boundary violated")

    return {
      "version":"1.0",
      "artifact_class":proto["output_contract"]["artifact_class"],
      "storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,
      "mode":"SYNTHETIC",
      "status":proto["output_contract"]["status"],
      "decision_id":did,
      "decision_at_utc":request["decision_at_utc"],
      "requested_combination_id":request["requested_combination_id"],
      "requested_market_data_candidate_id":base["requested_market_data_candidate_id"],
      "requested_kms_candidate_id":base["requested_kms_candidate_id"],
      "review_batch_id":base["review_batch_id"],
      "review_receipt_sha256":base["review_receipt_sha256"],
      "composite_dossier_sha256":base["composite_dossier_sha256"],
      "authorization_id":auth_id,
      "authorization_sha256":auth_sha,
      "authorizer_ref_sha256":base["authorizer_ref_sha256"],
      "authorization_status":base["authorization_status"],
      "base_authorization_binding_validated":base["authorization_binding_validated"],
      "dual_control_approval_validated":base["dual_control_approval_validated"],
      "exact_six_pair_coverage_validated":base["exact_six_pair_coverage_validated"],
      "lifecycle_full_chain_validated":True,
      "lifecycle_event_backups_validated":True,
      "lifecycle_current_authorization_validated":True,
      "lifecycle_event_count":lifecycle["event_count"],
      "lifecycle_head_sha256":lifecycle["head_sha256"],
      "lifecycle_current_status":lifecycle["current_status"],
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
    require_external(request_path,"lifecycle-integrated selection request")
    require_external(decision_store_root,"lifecycle-integrated decision store")
    if not request_path.is_file(): raise RuntimeError("lifecycle-integrated selection request missing")
    request=load(request_path)
    decision=evaluate_request(request)
    hits=forbidden_keys(decision,set(load(PROTO)["prohibited_keys"]))
    if hits: raise RuntimeError("integrated selection decision contains prohibited field: "+hits[0])
    target=decision_store_root.resolve()/"selection_lifecycle_decisions"/(decision["decision_id"]+".json")
    result=write_immutable_json(decision_store_root.resolve(),target,decision)
    return {
      "status":"SYNTHETIC_LIFECYCLE_SELECTION_DECISION_RECORDED" if result["status"]=="WRITTEN" else "IDEMPOTENT_REPLAY_ACCEPTED",
      "decision_id":decision["decision_id"],
      "decision_record_sha256":result["sha256"],
      "lifecycle_event_count":decision["lifecycle_event_count"],
      "lifecycle_head_sha256":decision["lifecycle_head_sha256"],
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
