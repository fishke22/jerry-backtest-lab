from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external, write_immutable_json, verify_backup, sha256_file

ROOT=Path(__file__).resolve().parents[1]
PROTO=ROOT/"config"/"jnu_private_selection_transition_prepare_protocol_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"

REQUEST_KEYS={
    "version","mode","synthetic_fixture","operation","prepare_id","prepared_at_utc",
    "decision_store_root","decision_record_path","decision_record_sha256",
    "requested_combination_id","lifecycle_expected_event_count","lifecycle_expected_head_sha256",
    "production_state_sha256"
}
SNAPSHOT_IDS={"PROVIDER_SELECTION_SHORTLIST","PRODUCTION_KEY_CUSTODY_CURRENT","PROVIDER_TERM_READINESS_CURRENT"}
HEX64=re.compile(r"^[0-9a-f]{64}$")
PREPARE_ID_RE=re.compile(r"^JNU_SELECTION_PREPARE_SYNTH_[A-Za-z0-9_-]+$")

def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise RuntimeError(f"{p} must contain an object")
    return x

def canonical_sha256(obj)->str:
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")).hexdigest()

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

def expected_pairs(shortlist:dict)->set[str]:
    return {p["id"]+"__"+k["id"] for p in shortlist["market_data_candidates"] for k in shortlist["key_custody_candidates"]}

def validate_decision(request:dict,proto:dict)->dict:
    root=Path(str(request["decision_store_root"]))
    path=Path(str(request["decision_record_path"]))
    require_external(root,"lifecycle-integrated decision store")
    require_external(path,"lifecycle-integrated decision record")
    if not path.is_absolute() or not root.is_absolute(): raise RuntimeError("decision store/path must be absolute")
    root=root.resolve();path=path.resolve()
    expected_dir=(root/"selection_lifecycle_decisions").resolve()
    if path.parent!=expected_dir: raise RuntimeError("decision record must be inside selection_lifecycle_decisions")
    if not path.is_file(): raise RuntimeError("lifecycle-integrated decision record missing")
    expected_sha=str(request["decision_record_sha256"])
    if not HEX64.fullmatch(expected_sha): raise RuntimeError("decision_record_sha256 invalid")
    if sha256_file(path)!=expected_sha: raise RuntimeError("decision record SHA-256 mismatch")
    if verify_backup(root,path).get("status")!="PASS": raise RuntimeError("decision record immutable backup/checksum invalid")
    d=load(path);c=proto["decision_contract"]
    for k in ["artifact_class","status","storage_scope","public_distribution_permitted","mode","selection_transition_permitted","selection_written","selected_combination_id","selected_market_data_provider","selected_key_custody_provider","production_state_mutated","real_activation_authorized","lifecycle_full_chain_validated","lifecycle_event_backups_validated","lifecycle_current_authorization_validated"]:
        if d.get(k)!=c[k]: raise RuntimeError("decision contract mismatch: "+k)
    pair=str(request["requested_combination_id"])
    if d.get("requested_combination_id")!=pair: raise RuntimeError("prepare pair does not match decision record")
    if d.get("requested_market_data_candidate_id")+"__"+d.get("requested_kms_candidate_id")!=pair:
        raise RuntimeError("decision candidate IDs do not reconstruct requested pair")
    count=request["lifecycle_expected_event_count"]
    if not isinstance(count,int) or count<1 or d.get("lifecycle_event_count")!=count:
        raise RuntimeError("lifecycle event-count binding mismatch")
    head=str(request["lifecycle_expected_head_sha256"])
    if not HEX64.fullmatch(head) or d.get("lifecycle_head_sha256")!=head:
        raise RuntimeError("lifecycle head SHA-256 binding mismatch")
    hits=forbidden_keys(d,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("decision record contains prohibited field: "+hits[0])
    return {"record":d,"sha256":expected_sha}

def validate_state_snapshots(request:dict,proto:dict)->tuple[dict,dict,dict,dict]:
    snaps=request["production_state_sha256"]
    if not isinstance(snaps,dict): raise RuntimeError("production_state_sha256 must be object")
    if set(snaps)!=SNAPSHOT_IDS: raise RuntimeError("production-state snapshots must cover exact authoritative surface")
    paths={
      "PROVIDER_SELECTION_SHORTLIST":SHORTLIST,
      "PRODUCTION_KEY_CUSTODY_CURRENT":KEY_CURRENT,
      "PROVIDER_TERM_READINESS_CURRENT":TERMS_CURRENT
    }
    verified={}
    for sid,p in paths.items():
        expected=str(snaps[sid])
        if not HEX64.fullmatch(expected): raise RuntimeError("production-state snapshot SHA invalid: "+sid)
        actual=sha256_file(p)
        if actual!=expected: raise RuntimeError("stale production-state snapshot: "+sid)
        verified[sid]={"path":str(p.relative_to(ROOT)),"sha256":actual}
    short=load(SHORTLIST);key=load(KEY_CURRENT);terms=load(TERMS_CURRENT)
    pre=proto["production_preconditions"]
    if short.get("selected_market_data_provider")!=pre["selected_market_data_provider"] or short.get("selected_key_custody_provider")!=pre["selected_key_custody_provider"]:
        raise RuntimeError("shortlist production selection state mutated")
    if key.get("production_enabled") is not pre["production_key_enabled"] or key.get("vendor")!=pre["production_key_vendor"] or key.get("region")!=pre["production_key_region"]:
        raise RuntimeError("production key state mutated")
    if terms.get("broker_auth_used") is not pre["broker_auth_used"] or terms.get("trading_permission_used") is not pre["trading_permission_used"] or terms.get("public_output_requested") is not pre["public_output_requested"]:
        raise RuntimeError("provider-term production boundary mutated")
    return verified,short,key,terms

def find_pair_metadata(shortlist:dict,pair:str)->tuple[dict,dict]:
    provider_id,kms_id=pair.split("__",1)
    p=next((x for x in shortlist["market_data_candidates"] if x["id"]==provider_id),None)
    k=next((x for x in shortlist["key_custody_candidates"] if x["id"]==kms_id),None)
    if p is None or k is None: raise RuntimeError("requested pair not found in shortlist")
    return p,k

def evaluate_request(request:dict)->dict:
    proto=load(PROTO)
    exact_keys(request,REQUEST_KEYS,"selection-transition PREPARE request")
    hits=forbidden_keys(request,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("prepare request contains prohibited field: "+hits[0])
    if request["mode"]!="SYNTHETIC" or request["synthetic_fixture"] is not True:
        raise RuntimeError("selection-transition prepare is synthetic-only")
    if request["operation"]!="PREPARE_ONLY":
        raise RuntimeError("COMMIT/APPLY unsupported; PREPARE_ONLY is the only operation")
    pid=str(request["prepare_id"])
    if not PREPARE_ID_RE.fullmatch(pid): raise RuntimeError("synthetic prepare_id invalid")
    parse_time(request["prepared_at_utc"],"prepared_at_utc")
    pair=str(request["requested_combination_id"])
    short=load(SHORTLIST)
    if pair not in expected_pairs(short): raise RuntimeError("requested pair not in frozen shortlist")

    decision=validate_decision(request,proto)
    snapshots,short,key,terms=validate_state_snapshots(request,proto)
    provider,kms=find_pair_metadata(short,pair)

    intended=[
      {
        "state_id":"PROVIDER_SELECTION_SHORTLIST",
        "field":"selected_market_data_provider",
        "from":"UNSELECTED",
        "preview_to":provider["id"],
        "mutation_class":"FUTURE_SELECTION_POINTER",
        "apply_supported":False
      },
      {
        "state_id":"PROVIDER_SELECTION_SHORTLIST",
        "field":"selected_key_custody_provider",
        "from":"UNSELECTED",
        "preview_to":kms["id"],
        "mutation_class":"FUTURE_SELECTION_POINTER",
        "apply_supported":False
      },
      {
        "state_id":"PRODUCTION_KEY_CUSTODY_CURRENT",
        "field_group":"vendor_region_control_class",
        "from":{"vendor":"UNSELECTED","region":"UNSELECTED","control_class":"UNSELECTED"},
        "preview_to":{"vendor":kms["vendor"],"region":kms["proposed_region"],"control_class":kms["control_class"]},
        "production_enabled_preview":False,
        "mutation_class":"FUTURE_KMS_SELECTION_CONFIGURATION",
        "schema_commit_authorized":False,
        "apply_supported":False
      },
      {
        "state_id":"PROVIDER_TERM_READINESS_CURRENT",
        "field":"provider_selected_status",
        "from":terms.get("provider_selected_status"),
        "preview_to":"REQUIRES_SEPARATE_REAL_EVIDENCE_REVALIDATION_BEFORE_FUTURE_COMMIT",
        "mutation_class":"FUTURE_REVALIDATION_REQUIREMENT_NOT_A_WRITABLE_VALUE",
        "apply_supported":False
      }
    ]

    return {
      "version":"1.0",
      "artifact_class":proto["output_contract"]["artifact_class"],
      "storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,
      "mode":"SYNTHETIC",
      "status":proto["output_contract"]["status"],
      "prepare_id":pid,
      "prepared_at_utc":request["prepared_at_utc"],
      "operation":"PREPARE_ONLY",
      "request_binding_sha256":canonical_sha256(request),
      "decision_id":decision["record"]["decision_id"],
      "decision_record_sha256":decision["sha256"],
      "lifecycle_event_count":request["lifecycle_expected_event_count"],
      "lifecycle_head_sha256":request["lifecycle_expected_head_sha256"],
      "requested_combination_id":pair,
      "requested_market_data_candidate_id":provider["id"],
      "requested_kms_candidate_id":kms["id"],
      "production_state_preconditions":snapshots,
      "compare_and_swap_required":True,
      "intended_mutations_preview":intended,
      "rollback_recovery":{
        "preimage_sha256_bound":True,
        "future_commit_requires_private_preimage_backup":True,
        "rollback_source":"PREIMAGE_BACKUP_PLUS_BOUND_SHA256",
        "prepare_stage_created_production_backup":False,
        "reason":"PREPARE_ONLY writes no production state"
      },
      "commit_capability":False,
      "apply_capability":False,
      "selection_transition_permitted":False,
      "selection_written":False,
      "selected_market_data_provider":"UNSELECTED",
      "selected_key_custody_provider":"UNSELECTED",
      "selected_combination_id":"UNSELECTED",
      "production_state_mutated":False,
      "credentials_connected":False,
      "kms_api_called":False,
      "key_created":False,
      "real_activation_manifest_generated":False,
      "real_activation_authorized":False
    }

def process(request_path:Path,prepare_store_root:Path)->dict:
    require_external(request_path,"selection-transition PREPARE request")
    require_external(prepare_store_root,"selection-transition PREPARE store")
    if not request_path.is_file(): raise RuntimeError("selection-transition PREPARE request missing")
    request=load(request_path)
    out=evaluate_request(request)
    hits=forbidden_keys(out,set(load(PROTO)["prohibited_keys"]))
    if hits: raise RuntimeError("prepare changeset contains prohibited field: "+hits[0])
    target=prepare_store_root.resolve()/"selection_transition_prepares"/(out["prepare_id"]+".json")
    result=write_immutable_json(prepare_store_root.resolve(),target,out)
    return {
      "status":"SYNTHETIC_PREPARE_CHANGESET_WRITTEN" if result["status"]=="WRITTEN" else "IDEMPOTENT_REPLAY_ACCEPTED",
      "prepare_id":out["prepare_id"],
      "changeset_sha256":result["sha256"],
      "commit_capability":False,
      "apply_capability":False,
      "selection_written":False,
      "production_state_mutated":False,
      "real_activation_authorized":False
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--request",type=Path,required=True)
    ap.add_argument("--prepare-store-root",type=Path,required=True)
    a=ap.parse_args()
    print(json.dumps(process(a.request,a.prepare_store_root),indent=2))

if __name__=="__main__":main()
