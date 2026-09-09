from __future__ import annotations
import argparse, hashlib, json, os, shutil, tempfile
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external, write_immutable_json, verify_backup, sha256_file

ROOT=Path(__file__).resolve().parents[1]
PROTO=ROOT/"config"/"jnu_private_selection_shadow_fault_simulation_protocol_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"

REQUEST_KEYS={
  "version","mode","synthetic_fixture","operation","simulation_id","evaluated_at_utc","fault_at","test_condition",
  "noop_store_root","noop_receipt_path","noop_receipt_sha256",
  "prepare_store_root","changeset_path","changeset_sha256",
  "decision_store_root","decision_record_path","decision_record_sha256",
  "shadow_root"
}
STATE_PATHS={
  "PROVIDER_SELECTION_SHORTLIST":SHORTLIST,
  "PRODUCTION_KEY_CUSTODY_CURRENT":KEY_CURRENT,
  "PROVIDER_TERM_READINESS_CURRENT":TERMS_CURRENT
}
HEX64=set("0123456789abcdef")

def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise RuntimeError(f"{p} must contain an object")
    return x

def exact_keys(x:dict,allowed:set[str],label:str)->None:
    extra=set(x)-allowed; missing=allowed-set(x)
    if extra: raise RuntimeError(label+" contains prohibited/unknown fields: "+",".join(sorted(extra)))
    if missing: raise RuntimeError(label+" missing required fields: "+",".join(sorted(missing)))

def valid_sha(s)->bool:
    s=str(s);return len(s)==64 and all(c in HEX64 for c in s)

def canonical_sha256(obj)->str:
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def parse_time(value,label:str):
    from datetime import datetime
    try:d=datetime.fromisoformat(str(value))
    except Exception as e: raise RuntimeError(label+" invalid") from e
    if d.tzinfo is None: raise RuntimeError(label+" must be timezone-aware")
    return d

def forbidden_keys(x,prohibited:set[str],path="root")->list[str]:
    hits=[]
    if isinstance(x,dict):
        for k,v in x.items():
            if str(k).lower() in prohibited:hits.append(path+"."+str(k))
            hits.extend(forbidden_keys(v,prohibited,path+"."+str(k)))
    elif isinstance(x,list):
        for i,v in enumerate(x):hits.extend(forbidden_keys(v,prohibited,f"{path}[{i}]"))
    return hits

def validate_external(root:Path,path:Path,sha:str,subdir:str,label:str)->dict:
    require_external(root,label+" store");require_external(path,label)
    if not root.is_absolute() or not path.is_absolute():raise RuntimeError(label+" store/path must be absolute")
    root=root.resolve();path=path.resolve()
    if path.parent!=(root/subdir).resolve():raise RuntimeError(label+" outside canonical store subdirectory")
    if not path.is_file():raise RuntimeError(label+" missing")
    if not valid_sha(sha) or sha256_file(path)!=sha:raise RuntimeError(label+" SHA-256 mismatch")
    if verify_backup(root,path).get("status")!="PASS":raise RuntimeError(label+" immutable backup/checksum invalid")
    return load(path)

def validate_lineage(req:dict,proto:dict)->tuple[dict,dict,dict]:
    n=validate_external(Path(str(req["noop_store_root"])),Path(str(req["noop_receipt_path"])),str(req["noop_receipt_sha256"]),"selection_transaction_noop_receipts","NOOP transaction receipt")
    for k,v in [("artifact_class",proto["input_contract"]["noop_receipt_artifact_class"]),("status",proto["input_contract"]["noop_receipt_status"]),("commit_authorized",False),("apply_authorized",False),("execution_capability",False),("production_state_mutated",False)]:
        if n.get(k)!=v:raise RuntimeError("NOOP receipt contract mismatch: "+k)
    c=validate_external(Path(str(req["prepare_store_root"])),Path(str(req["changeset_path"])),str(req["changeset_sha256"]),"selection_transition_prepares","PREPARE changeset")
    if c.get("artifact_class")!="JNU_SYNTHETIC_SELECTION_TRANSITION_PREPARE_CHANGESET" or c.get("status")!="SYNTHETIC_PREPARE_ONLY_CHANGESET_READY_NOT_COMMITTABLE":raise RuntimeError("PREPARE changeset contract mismatch")
    d=validate_external(Path(str(req["decision_store_root"])),Path(str(req["decision_record_path"])),str(req["decision_record_sha256"]),"selection_lifecycle_decisions","lifecycle-integrated decision")
    if d.get("artifact_class")!="JNU_SYNTHETIC_SELECTION_DECISION_LIFECYCLE_CURRENT_AUTH_RECORD" or d.get("status")!="SYNTHETIC_LIFECYCLE_CURRENT_AUTH_VALIDATED_NO_SELECTION":raise RuntimeError("decision contract mismatch")
    if n.get("changeset_sha256")!=req["changeset_sha256"] or c.get("decision_record_sha256")!=req["decision_record_sha256"] or n.get("decision_record_sha256")!=req["decision_record_sha256"]:raise RuntimeError("shadow simulation lineage SHA mismatch")
    for k in ["decision_id","requested_combination_id","requested_market_data_candidate_id","requested_kms_candidate_id","lifecycle_event_count","lifecycle_head_sha256"]:
        if n.get(k)!=d.get(k) or c.get(k)!=d.get(k):raise RuntimeError("shadow simulation lineage mismatch: "+k)
    return n,c,d

def state_bytes()->dict[str,bytes]:
    return {sid:p.read_bytes() for sid,p in STATE_PATHS.items()}

def state_hashes_from_bytes(b:dict[str,bytes])->dict[str,str]:
    return {sid:hashlib.sha256(raw).hexdigest() for sid,raw in b.items()}

def ensure_production_unchanged(before:dict[str,bytes])->dict[str,str]:
    after=state_bytes()
    if before!=after:raise RuntimeError("authoritative production state changed during shadow simulation")
    return state_hashes_from_bytes(after)

def init_shadow(shadow_root:Path,before:dict[str,bytes])->dict[str,Path]:
    require_external(shadow_root,"shadow simulation root")
    if shadow_root.exists():
        if not shadow_root.is_dir():raise RuntimeError("shadow_root must be directory")
        if any(shadow_root.iterdir()):raise RuntimeError("shadow_root must be empty or absent")
    else:shadow_root.mkdir(parents=True)
    sd=shadow_root/"state";sd.mkdir()
    out={}
    for sid,src in STATE_PATHS.items():
        p=sd/src.name;p.write_bytes(before[sid]);out[sid]=p
    return out

def acquire_shadow_lock(shadow_root:Path)->Path:
    p=shadow_root/".selection-shadow.lock"
    try:fd=os.open(str(p),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError as e:raise RuntimeError("shadow transaction lock contention") from e
    with os.fdopen(fd,"w") as f:f.write("synthetic-shadow-lock\n")
    return p

def release_lock(p:Path|None)->None:
    if p is not None:
        try:p.unlink()
        except FileNotFoundError:pass

def shadow_hashes(paths:dict[str,Path])->dict[str,str]:
    return {sid:sha256_file(p) for sid,p in paths.items()}

def expected_preimage(changeset:dict)->dict[str,str]:
    snaps=changeset.get("production_state_preconditions")
    if not isinstance(snaps,dict) or set(snaps)!=set(STATE_PATHS):raise RuntimeError("changeset CAS surface invalid")
    out={}
    for sid,prod in STATE_PATHS.items():
        row=snaps[sid]
        if row.get("path")!=str(prod.relative_to(ROOT)):raise RuntimeError("changeset CAS path mismatch: "+sid)
        sha=str(row.get("sha256",""))
        if not valid_sha(sha):raise RuntimeError("changeset CAS hash invalid: "+sid)
        out[sid]=sha
    return out

def backup_shadow(shadow_root:Path,paths:dict[str,Path])->dict[str,dict]:
    bd=shadow_root/"preimage_backups";bd.mkdir()
    out={}
    for sid,p in paths.items():
        target=bd/p.name;shutil.copy2(p,target);sha=sha256_file(target)
        side=Path(str(target)+".sha256");side.write_text(sha+"\n",encoding="utf-8")
        out[sid]={"path":target,"sha256":sha,"sidecar":side}
    return out

def verify_backups(backups:dict[str,dict],expected:dict[str,str])->None:
    for sid,row in backups.items():
        p=row["path"];side=row["sidecar"]
        if not p.is_file() or not side.is_file():raise RuntimeError("shadow preimage backup missing: "+sid)
        sha=sha256_file(p)
        if sha!=expected[sid] or side.read_text(encoding="utf-8").strip()!=sha:raise RuntimeError("shadow preimage backup corrupted: "+sid)

def atomic_json_write(path:Path,obj:dict)->None:
    fd,tmp=tempfile.mkstemp(prefix=path.name+".",dir=str(path.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(obj,f,indent=2,ensure_ascii=False);f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def pair_metadata(decision:dict)->tuple[dict,dict]:
    short=load(SHORTLIST)
    pid=decision["requested_market_data_candidate_id"];kid=decision["requested_kms_candidate_id"]
    p=next((x for x in short["market_data_candidates"] if x["id"]==pid),None)
    k=next((x for x in short["key_custody_candidates"] if x["id"]==kid),None)
    if p is None or k is None:raise RuntimeError("requested pair not in shortlist")
    return p,k

def mutate_shadow(paths:dict[str,Path],decision:dict,fault_at:str)->dict[str,str]:
    provider,kms=pair_metadata(decision)
    s=load(paths["PROVIDER_SELECTION_SHORTLIST"]);s["selected_market_data_provider"]=provider["id"];s["selected_key_custody_provider"]=kms["id"];atomic_json_write(paths["PROVIDER_SELECTION_SHORTLIST"],s)
    if fault_at=="MUTATION_SET":raise RuntimeError("INJECTED_MUTATION_SET_AFTER_FIRST_SHADOW_WRITE")
    k=load(paths["PRODUCTION_KEY_CUSTODY_CURRENT"]);k["vendor"]=kms["vendor"];k["region"]=kms["proposed_region"];k["control_class"]=kms["control_class"];k["production_enabled"]=False;atomic_json_write(paths["PRODUCTION_KEY_CUSTODY_CURRENT"],k)
    t=load(paths["PROVIDER_TERM_READINESS_CURRENT"]);t["provider_selected_status"]="SYNTHETIC_SHADOW_SELECTED_NOT_PRODUCTION";atomic_json_write(paths["PROVIDER_TERM_READINESS_CURRENT"],t)
    return shadow_hashes(paths)

def verify_shadow_mutation(paths:dict[str,Path],decision:dict)->None:
    s=load(paths["PROVIDER_SELECTION_SHORTLIST"]);k=load(paths["PRODUCTION_KEY_CUSTODY_CURRENT"]);t=load(paths["PROVIDER_TERM_READINESS_CURRENT"])
    if s.get("selected_market_data_provider")!=decision["requested_market_data_candidate_id"] or s.get("selected_key_custody_provider")!=decision["requested_kms_candidate_id"]:raise RuntimeError("shadow shortlist post-write verification failed")
    _,kms=pair_metadata(decision)
    if k.get("vendor")!=kms["vendor"] or k.get("region")!=kms["proposed_region"] or k.get("control_class")!=kms["control_class"] or k.get("production_enabled") is not False:raise RuntimeError("shadow key-profile post-write verification failed")
    if t.get("provider_selected_status")!="SYNTHETIC_SHADOW_SELECTED_NOT_PRODUCTION":raise RuntimeError("shadow provider-term post-write verification failed")

def rollback_shadow(paths:dict[str,Path],backups:dict[str,dict],expected:dict[str,str],inject_interruption:bool=False)->bool:
    verify_backups(backups,expected)
    interrupted=False
    order=list(STATE_PATHS)
    for i,sid in enumerate(order):
        shutil.copy2(backups[sid]["path"],paths[sid])
        if inject_interruption and i==0:
            interrupted=True
            break
    if interrupted:
        for sid in order:
            if sha256_file(paths[sid])!=expected[sid]:shutil.copy2(backups[sid]["path"],paths[sid])
    if shadow_hashes(paths)!=expected:raise RuntimeError("shadow rollback did not restore exact preimage")
    return interrupted

def make_receipt(req,noop,changeset,decision,before_hashes,shadow_preimage,shadow_final,status,steps,rollback_performed,rollback_resumed,production_after):
    return {
      "version":"1.0","artifact_class":"JNU_SYNTHETIC_SELECTION_TRANSACTION_SHADOW_SIMULATION_RECEIPT","storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,"mode":"SYNTHETIC_SHADOW_ONLY","status":status,
      "simulation_id":req["simulation_id"],"evaluated_at_utc":req["evaluated_at_utc"],"request_binding_sha256":canonical_sha256(req),
      "fault_at":req["fault_at"],"test_condition":req["test_condition"],
      "noop_transaction_id":noop["transaction_id"],"noop_receipt_sha256":req["noop_receipt_sha256"],
      "prepare_id":changeset["prepare_id"],"changeset_sha256":req["changeset_sha256"],
      "decision_id":decision["decision_id"],"decision_record_sha256":req["decision_record_sha256"],
      "requested_combination_id":decision["requested_combination_id"],"lifecycle_event_count":decision["lifecycle_event_count"],"lifecycle_head_sha256":decision["lifecycle_head_sha256"],
      "production_sha256_before":before_hashes,"production_sha256_after":production_after,"production_unchanged":before_hashes==production_after,
      "shadow_preimage_sha256":shadow_preimage,"shadow_final_sha256":shadow_final,
      "transaction_sequence":steps,"rollback_performed":rollback_performed,"rollback_interruption_resumed":rollback_resumed,
      "real_commit_capability":False,"real_apply_capability":False,"production_lock_acquired":False,"production_backup_created":False,
      "production_state_mutated":False,"credentials_connected":False,"kms_api_called":False,"real_key_created":False,"real_activation_authorized":False
    }

def evaluate_request(req:dict)->dict:
    proto=load(PROTO);exact_keys(req,REQUEST_KEYS,"shadow simulation request")
    hits=forbidden_keys(req,set(proto["prohibited_keys"]))
    if hits:raise RuntimeError("shadow simulation request contains prohibited field: "+hits[0])
    if req["mode"]!="SYNTHETIC" or req["synthetic_fixture"] is not True or req["operation"]!="SHADOW_FAULT_SIMULATION":raise RuntimeError("shadow simulator is synthetic-only")
    if req["fault_at"] not in proto["fault_injection"]["allowed_fault_points"]:raise RuntimeError("invalid fault_at")
    if req["test_condition"] not in proto["test_conditions"]["allowed"]:raise RuntimeError("invalid test_condition")
    if not str(req["simulation_id"]).startswith("JNU_SELECTION_SHADOW_SIM_SYNTH_"):raise RuntimeError("invalid simulation_id")
    parse_time(req["evaluated_at_utc"],"evaluated_at_utc")
    shadow_root=Path(str(req["shadow_root"]))
    noop,changeset,decision=validate_lineage(req,proto)
    before_bytes=state_bytes();before_hashes=state_hashes_from_bytes(before_bytes)
    expected=expected_preimage(changeset)
    if before_hashes!=expected:raise RuntimeError("authoritative production state is stale against PREPARE CAS")
    paths=init_shadow(shadow_root,before_bytes)
    if req["test_condition"]=="STALE_SHADOW_CAS":
        p=paths["PROVIDER_SELECTION_SHORTLIST"];p.write_bytes(p.read_bytes()+b" ")
    pre=expected.copy();lock=None;backups=None;rollback=False;resumed=False
    steps=[]
    def step(name,status):steps.append({"sequence":len(steps)+1,"step":name,"status":status,"production_effect":False})
    try:
        if req["fault_at"]=="LOCK_ACQUISITION":
            step("LOCK_ACQUISITION","INJECTED_FAULT_NO_LOCK")
            for name in proto["transaction_sequence"][1:]:step(name,"NOT_REACHED")
            prod_after=ensure_production_unchanged(before_bytes)
            return make_receipt(req,noop,changeset,decision,before_hashes,pre,shadow_hashes(paths),proto["statuses"]["fault_no_mutation"],steps,False,False,prod_after)
        lock=acquire_shadow_lock(shadow_root);step("LOCK_ACQUISITION","SHADOW_LOCK_ACQUIRED")
        if req["fault_at"]=="CAS_VERIFICATION":
            step("CAS_VERIFICATION","INJECTED_FAULT_BEFORE_CAS_ACCEPT")
            for name in proto["transaction_sequence"][2:]:step(name,"NOT_REACHED")
            prod_after=ensure_production_unchanged(before_bytes)
            return make_receipt(req,noop,changeset,decision,before_hashes,pre,shadow_hashes(paths),proto["statuses"]["fault_no_mutation"],steps,False,False,prod_after)
        if shadow_hashes(paths)!=expected:
            step("CAS_VERIFICATION","STALE_SHADOW_CAS_REJECTED")
            for name in proto["transaction_sequence"][2:]:step(name,"NOT_REACHED")
            prod_after=ensure_production_unchanged(before_bytes)
            return make_receipt(req,noop,changeset,decision,before_hashes,pre,shadow_hashes(paths),proto["statuses"]["stale_shadow_cas"],steps,False,False,prod_after)
        step("CAS_VERIFICATION","PASS")
        backups=backup_shadow(shadow_root,paths)
        if req["test_condition"]=="CORRUPT_PREIMAGE_BACKUP":
            first=backups["PROVIDER_SELECTION_SHORTLIST"]["path"];first.write_bytes(first.read_bytes()+b"CORRUPT")
        if req["fault_at"]=="PRIVATE_PREIMAGE_BACKUP":
            step("PRIVATE_PREIMAGE_BACKUP","INJECTED_FAULT_AFTER_BACKUP_CREATE")
            for name in proto["transaction_sequence"][3:]:step(name,"NOT_REACHED")
            prod_after=ensure_production_unchanged(before_bytes)
            return make_receipt(req,noop,changeset,decision,before_hashes,pre,shadow_hashes(paths),proto["statuses"]["fault_no_mutation"],steps,False,False,prod_after)
        try:verify_backups(backups,expected)
        except RuntimeError:
            step("PRIVATE_PREIMAGE_BACKUP","BACKUP_CHECKSUM_REJECTED")
            for name in proto["transaction_sequence"][3:]:step(name,"NOT_REACHED")
            prod_after=ensure_production_unchanged(before_bytes)
            return make_receipt(req,noop,changeset,decision,before_hashes,pre,shadow_hashes(paths),proto["statuses"]["corrupt_backup"],steps,False,False,prod_after)
        step("PRIVATE_PREIMAGE_BACKUP","PASS")
        try:
            mutate_shadow(paths,decision,req["fault_at"]);step("MUTATION_SET","PASS")
        except RuntimeError as e:
            if "INJECTED_MUTATION_SET" not in str(e):raise
            step("MUTATION_SET","INJECTED_FAULT_AFTER_FIRST_SHADOW_WRITE")
            step("POST_WRITE_VERIFICATION","NOT_REACHED")
            resumed=rollback_shadow(paths,backups,expected,False);rollback=True;step("ROLLBACK_ON_PARTIAL_FAILURE","ROLLBACK_COMPLETE")
            step("FINAL_TRANSACTION_RECEIPT","IMMUTABLE_RECEIPT")
            prod_after=ensure_production_unchanged(before_bytes)
            return make_receipt(req,noop,changeset,decision,before_hashes,pre,shadow_hashes(paths),proto["statuses"]["fault_rolled_back"],steps,rollback,resumed,prod_after)
        if req["fault_at"]=="POST_WRITE_VERIFICATION":
            step("POST_WRITE_VERIFICATION","INJECTED_FAULT")
            resumed=rollback_shadow(paths,backups,expected,False);rollback=True;step("ROLLBACK_ON_PARTIAL_FAILURE","ROLLBACK_COMPLETE")
            step("FINAL_TRANSACTION_RECEIPT","IMMUTABLE_RECEIPT")
            prod_after=ensure_production_unchanged(before_bytes)
            return make_receipt(req,noop,changeset,decision,before_hashes,pre,shadow_hashes(paths),proto["statuses"]["fault_rolled_back"],steps,rollback,resumed,prod_after)
        verify_shadow_mutation(paths,decision);step("POST_WRITE_VERIFICATION","PASS")
        if req["fault_at"]=="ROLLBACK_ON_PARTIAL_FAILURE":
            resumed=rollback_shadow(paths,backups,expected,True);rollback=True;step("ROLLBACK_ON_PARTIAL_FAILURE","INJECTED_INTERRUPTION_RESUMED_ROLLBACK_COMPLETE")
            step("FINAL_TRANSACTION_RECEIPT","IMMUTABLE_RECEIPT")
            prod_after=ensure_production_unchanged(before_bytes)
            return make_receipt(req,noop,changeset,decision,before_hashes,pre,shadow_hashes(paths),proto["statuses"]["fault_rolled_back"],steps,rollback,resumed,prod_after)
        step("ROLLBACK_ON_PARTIAL_FAILURE","NOT_REQUIRED")
        if req["fault_at"]=="FINAL_TRANSACTION_RECEIPT":
            rollback_shadow(paths,backups,expected,False);rollback=True;steps[-1]={"sequence":6,"step":"ROLLBACK_ON_PARTIAL_FAILURE","status":"ROLLBACK_DUE_TO_INJECTED_RECEIPT_WRITE_FAULT","production_effect":False}
            step("FINAL_TRANSACTION_RECEIPT","INJECTED_FIRST_WRITE_FAULT_RETRY_IMMUTABLE_RECEIPT")
            prod_after=ensure_production_unchanged(before_bytes)
            return make_receipt(req,noop,changeset,decision,before_hashes,pre,shadow_hashes(paths),proto["statuses"]["fault_rolled_back"],steps,rollback,False,prod_after)
        step("FINAL_TRANSACTION_RECEIPT","IMMUTABLE_RECEIPT")
        prod_after=ensure_production_unchanged(before_bytes)
        return make_receipt(req,noop,changeset,decision,before_hashes,pre,shadow_hashes(paths),proto["statuses"]["success"],steps,False,False,prod_after)
    finally:
        release_lock(lock)

def process(request_path:Path,receipt_store_root:Path)->dict:
    require_external(request_path,"shadow simulation request");require_external(receipt_store_root,"shadow simulation receipt store")
    if not request_path.is_file():raise RuntimeError("shadow simulation request missing")
    req=load(request_path)
    target=receipt_store_root.resolve()/"selection_shadow_simulation_receipts"/(req.get("simulation_id","INVALID")+".json")
    if target.is_file():
        existing=load(target)
        if existing.get("request_binding_sha256")!=canonical_sha256(req):raise RuntimeError("same simulation_id reused with different request")
        return {"status":"IDEMPOTENT_REPLAY_ACCEPTED","simulation_id":existing["simulation_id"],"receipt_sha256":sha256_file(target),"simulation_status":existing["status"],"production_state_mutated":False}
    receipt=evaluate_request(req)
    result=write_immutable_json(receipt_store_root.resolve(),target,receipt)
    return {"status":"SHADOW_SIMULATION_RECEIPT_WRITTEN","simulation_id":receipt["simulation_id"],"receipt_sha256":result["sha256"],"simulation_status":receipt["status"],"rollback_performed":receipt["rollback_performed"],"production_state_mutated":False,"real_activation_authorized":False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--request",type=Path,required=True);ap.add_argument("--receipt-store-root",type=Path,required=True);a=ap.parse_args()
    print(json.dumps(process(a.request,a.receipt_store_root),indent=2))
if __name__=="__main__":main()
