from __future__ import annotations
import argparse, json, re
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external, write_immutable_json, verify_backup, sha256_file

ROOT=Path(__file__).resolve().parents[1]
PROTO=ROOT/"config"/"jnu_private_selection_transaction_executor_noop_protocol_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"

REQUEST_KEYS={
  "version","mode","synthetic_fixture","operation","transaction_id","evaluated_at_utc",
  "ceremony_store_root","ceremony_receipt_path","ceremony_receipt_sha256",
  "prepare_store_root","changeset_path","changeset_sha256",
  "decision_store_root","decision_record_path","decision_record_sha256"
}
SNAPSHOT_IDS={"PROVIDER_SELECTION_SHORTLIST","PRODUCTION_KEY_CUSTODY_CURRENT","PROVIDER_TERM_READINESS_CURRENT"}
HEX64=re.compile(r"^[0-9a-f]{64}$")
TX_RE=re.compile(r"^JNU_SELECTION_TX_NOOP_SYNTH_[A-Za-z0-9_-]+$")

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

def validate_external(root:Path,path:Path,sha:str,subdir:str,label:str)->dict:
    require_external(root,label+" store");require_external(path,label)
    if not root.is_absolute() or not path.is_absolute(): raise RuntimeError(label+" store/path must be absolute")
    root=root.resolve();path=path.resolve()
    if path.parent!=(root/subdir).resolve(): raise RuntimeError(label+" outside canonical store subdirectory")
    if not path.is_file(): raise RuntimeError(label+" missing")
    if not HEX64.fullmatch(sha) or sha256_file(path)!=sha: raise RuntimeError(label+" SHA-256 mismatch")
    if verify_backup(root,path).get("status")!="PASS": raise RuntimeError(label+" immutable backup/checksum invalid")
    return load(path)

def validate_ceremony(req:dict,proto:dict)->dict:
    c=validate_external(Path(str(req["ceremony_store_root"])),Path(str(req["ceremony_receipt_path"])),str(req["ceremony_receipt_sha256"]),"commit_authorization_ceremonies","commit-authorization ceremony receipt")
    cc=proto["ceremony_contract"]
    for k in ["artifact_class","status","storage_scope","public_distribution_permitted","mode","authorization_status","commit_authorized","apply_authorized","execution_capability","selection_transition_permitted","selection_written","selected_combination_id","production_state_mutated","real_activation_authorized"]:
        if c.get(k)!=cc[k]: raise RuntimeError("ceremony contract mismatch: "+k)
    hits=forbidden_keys(c,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("ceremony receipt contains prohibited field: "+hits[0])
    return c

def validate_changeset(req:dict,ceremony:dict)->dict:
    c=validate_external(Path(str(req["prepare_store_root"])),Path(str(req["changeset_path"])),str(req["changeset_sha256"]),"selection_transition_prepares","PREPARE changeset")
    if c.get("artifact_class")!="JNU_SYNTHETIC_SELECTION_TRANSITION_PREPARE_CHANGESET" or c.get("status")!="SYNTHETIC_PREPARE_ONLY_CHANGESET_READY_NOT_COMMITTABLE":
        raise RuntimeError("PREPARE changeset contract mismatch")
    for k,v in [("commit_capability",False),("apply_capability",False),("selection_transition_permitted",False),("selection_written",False),("selected_combination_id","UNSELECTED"),("production_state_mutated",False),("real_activation_authorized",False)]:
        if c.get(k)!=v: raise RuntimeError("PREPARE changeset boundary mismatch: "+k)
    if ceremony.get("changeset_sha256")!=req["changeset_sha256"] or ceremony.get("prepare_id")!=c.get("prepare_id"):
        raise RuntimeError("ceremony / changeset lineage mismatch")
    return c

def validate_decision(req:dict,ceremony:dict,changeset:dict)->dict:
    d=validate_external(Path(str(req["decision_store_root"])),Path(str(req["decision_record_path"])),str(req["decision_record_sha256"]),"selection_lifecycle_decisions","lifecycle-integrated decision")
    if d.get("artifact_class")!="JNU_SYNTHETIC_SELECTION_DECISION_LIFECYCLE_CURRENT_AUTH_RECORD" or d.get("status")!="SYNTHETIC_LIFECYCLE_CURRENT_AUTH_VALIDATED_NO_SELECTION":
        raise RuntimeError("decision contract mismatch")
    for k,v in [("selection_transition_permitted",False),("selection_written",False),("selected_combination_id","UNSELECTED"),("production_state_mutated",False),("real_activation_authorized",False)]:
        if d.get(k)!=v: raise RuntimeError("decision boundary mismatch: "+k)
    if ceremony.get("decision_record_sha256")!=req["decision_record_sha256"] or changeset.get("decision_record_sha256")!=req["decision_record_sha256"]:
        raise RuntimeError("decision SHA lineage mismatch")
    for k in ["decision_id","requested_combination_id","requested_market_data_candidate_id","requested_kms_candidate_id","lifecycle_event_count","lifecycle_head_sha256"]:
        if ceremony.get(k)!=d.get(k) or changeset.get(k)!=d.get(k): raise RuntimeError("transaction lineage mismatch: "+k)
    return d

def verify_cas(ceremony:dict,changeset:dict)->dict:
    ceremony_cas=ceremony.get("production_state_cas_sha256")
    snaps=changeset.get("production_state_preconditions")
    if not isinstance(ceremony_cas,dict) or set(ceremony_cas)!=SNAPSHOT_IDS: raise RuntimeError("ceremony CAS surface invalid")
    if not isinstance(snaps,dict) or set(snaps)!=SNAPSHOT_IDS: raise RuntimeError("changeset CAS surface invalid")
    paths={"PROVIDER_SELECTION_SHORTLIST":SHORTLIST,"PRODUCTION_KEY_CUSTODY_CURRENT":KEY_CURRENT,"PROVIDER_TERM_READINESS_CURRENT":TERMS_CURRENT}
    out={}
    for sid,p in paths.items():
        row=snaps[sid]
        if row.get("path")!=str(p.relative_to(ROOT)): raise RuntimeError("changeset CAS path mismatch: "+sid)
        expected=str(row.get("sha256",""))
        if not HEX64.fullmatch(expected) or ceremony_cas.get(sid)!=expected: raise RuntimeError("ceremony/changeset CAS mismatch: "+sid)
        actual=sha256_file(p)
        if actual!=expected: raise RuntimeError("stale production-state CAS: "+sid)
        out[sid]={"expected_sha256":expected,"actual_sha256":actual,"match":True}
    short=load(SHORTLIST);key=load(KEY_CURRENT);terms=load(TERMS_CURRENT)
    if short.get("selected_market_data_provider")!="UNSELECTED" or short.get("selected_key_custody_provider")!="UNSELECTED": raise RuntimeError("selection state already mutated")
    if key.get("production_enabled") is not False or key.get("vendor")!="UNSELECTED" or key.get("region")!="UNSELECTED": raise RuntimeError("production key state already mutated")
    if terms.get("broker_auth_used") is not False or terms.get("trading_permission_used") is not False or terms.get("public_output_requested") is not False: raise RuntimeError("provider-term production boundary mutated")
    return out

def evaluate_request(req:dict)->dict:
    proto=load(PROTO);exact_keys(req,REQUEST_KEYS,"NOOP transaction request")
    hits=forbidden_keys(req,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("NOOP transaction request contains prohibited field: "+hits[0])
    if req["mode"]!="SYNTHETIC" or req["synthetic_fixture"] is not True: raise RuntimeError("transaction executor is synthetic-only")
    if req["operation"]!="NOOP_DRY_RUN": raise RuntimeError("only NOOP_DRY_RUN is supported")
    txid=str(req["transaction_id"])
    if not TX_RE.fullmatch(txid): raise RuntimeError("synthetic transaction_id invalid")
    parse_time(req["evaluated_at_utc"],"evaluated_at_utc")
    ceremony=validate_ceremony(req,proto)
    changeset=validate_changeset(req,ceremony)
    decision=validate_decision(req,ceremony,changeset)
    cas=verify_cas(ceremony,changeset)

    sequence=[
      {"sequence":1,"step":"LOCK_ACQUISITION","status":"NOT_EXECUTED_DISABLED_AUTHORIZATION","production_effect":False},
      {"sequence":2,"step":"CAS_VERIFICATION","status":"EXECUTED_READ_ONLY","production_effect":False},
      {"sequence":3,"step":"PRIVATE_PREIMAGE_BACKUP","status":"NOT_EXECUTED_DISABLED_AUTHORIZATION","production_effect":False},
      {"sequence":4,"step":"MUTATION_SET","status":"NOT_EXECUTED_DISABLED_AUTHORIZATION","production_effect":False},
      {"sequence":5,"step":"POST_WRITE_VERIFICATION","status":"NOT_APPLICABLE_NO_WRITE","production_effect":False},
      {"sequence":6,"step":"ROLLBACK_ON_PARTIAL_FAILURE","status":"NOT_APPLICABLE_NO_WRITE","production_effect":False},
      {"sequence":7,"step":"FINAL_TRANSACTION_RECEIPT","status":"IMMUTABLE_REPO_EXTERNAL_NOOP_RECEIPT","production_effect":False}
    ]
    return {
      "version":"1.0","artifact_class":proto["output_contract"]["artifact_class"],"storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,"mode":"SYNTHETIC","status":proto["output_contract"]["status"],
      "transaction_id":txid,"evaluated_at_utc":req["evaluated_at_utc"],
      "ceremony_id":ceremony["ceremony_id"],"ceremony_receipt_sha256":req["ceremony_receipt_sha256"],
      "prepare_id":changeset["prepare_id"],"changeset_sha256":req["changeset_sha256"],
      "decision_id":decision["decision_id"],"decision_record_sha256":req["decision_record_sha256"],
      "requested_combination_id":decision["requested_combination_id"],"requested_market_data_candidate_id":decision["requested_market_data_candidate_id"],"requested_kms_candidate_id":decision["requested_kms_candidate_id"],
      "lifecycle_event_count":decision["lifecycle_event_count"],"lifecycle_head_sha256":decision["lifecycle_head_sha256"],
      "production_state_cas_verification":cas,"transaction_sequence":sequence,
      "lock_acquired":False,"production_preimage_backup_created":False,"mutation_attempted":False,"mutation_applied":False,
      "post_write_verification_performed":False,"rollback_performed":False,
      "authorization_status":"SYNTHETIC_DISABLED","commit_authorized":False,"apply_authorized":False,"execution_capability":False,
      "selection_transition_permitted":False,"selection_written":False,"selected_market_data_provider":"UNSELECTED",
      "selected_key_custody_provider":"UNSELECTED","selected_combination_id":"UNSELECTED","production_state_mutated":False,
      "credentials_connected":False,"kms_api_called":False,"key_created":False,"real_activation_manifest_generated":False,"real_activation_authorized":False
    }

def process(request_path:Path,transaction_store_root:Path)->dict:
    require_external(request_path,"NOOP transaction request");require_external(transaction_store_root,"NOOP transaction store")
    if not request_path.is_file(): raise RuntimeError("NOOP transaction request missing")
    receipt=evaluate_request(load(request_path))
    target=transaction_store_root.resolve()/"selection_transaction_noop_receipts"/(receipt["transaction_id"]+".json")
    result=write_immutable_json(transaction_store_root.resolve(),target,receipt)
    return {"status":"NOOP_TRANSACTION_RECEIPT_WRITTEN" if result["status"]=="WRITTEN" else "IDEMPOTENT_REPLAY_ACCEPTED",
      "transaction_id":receipt["transaction_id"],"transaction_receipt_sha256":result["sha256"],
      "execution_status":receipt["status"],"lock_acquired":False,"production_preimage_backup_created":False,
      "mutation_attempted":False,"mutation_applied":False,"production_state_mutated":False,"real_activation_authorized":False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--request",type=Path,required=True);ap.add_argument("--transaction-store-root",type=Path,required=True);a=ap.parse_args()
    print(json.dumps(process(a.request,a.transaction_store_root),indent=2))
if __name__=="__main__":main()
