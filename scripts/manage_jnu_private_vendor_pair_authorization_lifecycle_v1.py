from __future__ import annotations
import argparse, hashlib, json, re
from datetime import datetime
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external, write_immutable_json, sha256_file

ROOT=Path(__file__).resolve().parents[1]
PROTO=ROOT/"config"/"jnu_private_vendor_pair_selection_authorization_lifecycle_protocol_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"

EVENT_REQUEST_KEYS={"version","mode","synthetic_fixture","event_id","event_type","event_at_utc","authorization_path","authorization_sha256","target_authorization_id","revocation_reason","revocation_authorizer_reference","revocation_authorizer_role","revocation_attestation"}
AUTH_KEYS={"version","artifact_class","mode","synthetic_fixture","authorization_id","authorization_scope","authorization_status","authorizer_role","authorizer_reference","authorizer_attestation","review_batch_id","review_receipt_sha256","composite_dossier_sha256","authorized_combination_id","issued_at_utc","valid_from_utc","expires_at_utc","selection_write_permitted","real_selection_authorized"}
HEX64=re.compile(r"^[0-9a-f]{64}$")
EVENT_ID_RE=re.compile(r"^JNU_AUTH_EVENT_SYNTH_[A-Za-z0-9_-]+$")

def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise RuntimeError(f"{p} must contain an object")
    return x

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

def parse_time(value,label:str)->datetime:
    try:d=datetime.fromisoformat(str(value))
    except Exception as e: raise RuntimeError(label+" invalid") from e
    if d.tzinfo is None: raise RuntimeError(label+" must be timezone-aware")
    return d

def shortlist_pairs()->set[str]:
    s=load(SHORTLIST)
    return {p["id"]+"__"+k["id"] for p in s["market_data_candidates"] for k in s["key_custody_candidates"]}

def validate_production_state()->None:
    short=load(SHORTLIST);key=load(KEY_CURRENT);terms=load(TERMS_CURRENT)
    if short.get("selected_market_data_provider")!="UNSELECTED" or short.get("selected_key_custody_provider")!="UNSELECTED":
        raise RuntimeError("provider/KMS selection state already mutated")
    if key.get("production_enabled") is not False or key.get("vendor")!="UNSELECTED" or key.get("region")!="UNSELECTED":
        raise RuntimeError("production key state already mutated")
    if terms.get("broker_auth_used") is not False or terms.get("trading_permission_used") is not False or terms.get("public_output_requested") is not False:
        raise RuntimeError("broker/trading/public-output state violates lifecycle gate")

def validate_authorization_artifact(path:Path,expected_sha:str,proto:dict)->dict:
    if not path.is_absolute(): raise RuntimeError("authorization_path must be absolute")
    require_external(path,"authorization artifact")
    if not path.is_file(): raise RuntimeError("authorization artifact missing")
    if not HEX64.fullmatch(expected_sha): raise RuntimeError("authorization_sha256 invalid")
    actual=sha256_file(path)
    if actual!=expected_sha: raise RuntimeError("authorization artifact SHA-256 mismatch")
    a=load(path);exact_keys(a,AUTH_KEYS,"authorization artifact")
    hits=forbidden_keys(a,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("authorization artifact contains prohibited field: "+hits[0])
    c=proto["authorization_contract"]
    for k in ["artifact_class","mode","synthetic_fixture","authorization_scope","authorization_status","authorizer_role","authorizer_attestation","selection_write_permitted","real_selection_authorized"]:
        if a.get(k)!=c[k]: raise RuntimeError("authorization artifact frozen value mismatch: "+k)
    aid=str(a.get("authorization_id",""))
    if not aid: raise RuntimeError("authorization_id required")
    if not str(a.get("authorizer_reference","")): raise RuntimeError("authorizer_reference required")
    if not str(a.get("review_batch_id","")): raise RuntimeError("review_batch_id required")
    if not HEX64.fullmatch(str(a.get("review_receipt_sha256",""))): raise RuntimeError("review_receipt_sha256 invalid")
    if not HEX64.fullmatch(str(a.get("composite_dossier_sha256",""))): raise RuntimeError("composite_dossier_sha256 invalid")
    pair=str(a.get("authorized_combination_id",""))
    if pair not in shortlist_pairs(): raise RuntimeError("authorization pair not in shortlist")
    issued=parse_time(a.get("issued_at_utc"),"authorization issued_at_utc")
    valid=parse_time(a.get("valid_from_utc"),"authorization valid_from_utc")
    expiry=parse_time(a.get("expires_at_utc"),"authorization expires_at_utc")
    if issued>valid or valid>=expiry: raise RuntimeError("authorization validity chronology invalid")
    return {"artifact":a,"sha256":actual,"issued":issued,"valid":valid,"expiry":expiry}

def event_files(store_root:Path)->list[Path]:
    d=store_root.resolve()/"authorization_events"
    if not d.exists(): return []
    return sorted([p for p in d.iterdir() if p.is_file() and p.suffix==".json"])

def audit_chain(store_root:Path,at_time:datetime|None=None)->dict:
    require_external(store_root,"authorization lifecycle store")
    proto=load(PROTO)
    files=event_files(store_root)
    parent="GENESIS";last_time=None;seen_events=set();seen_auth=set()
    active=None
    history=[]
    for idx,p in enumerate(files,1):
        e=load(p)
        hits=forbidden_keys(e,set(proto["prohibited_keys"]))
        if hits: raise RuntimeError("lifecycle event contains prohibited field: "+hits[0])
        if e.get("artifact_class")!="JNU_REDACTED_SYNTHETIC_AUTHORIZATION_LIFECYCLE_EVENT" or e.get("mode")!="SYNTHETIC":
            raise RuntimeError("lifecycle event artifact contract mismatch")
        if e.get("event_sequence")!=idx: raise RuntimeError("authorization event sequence gap/reorder detected")
        expected_name=f"{idx:06d}_{e.get('event_id')}.json"
        if p.name!=expected_name: raise RuntimeError("authorization event filename/sequence mismatch")
        eid=e.get("event_id")
        if not isinstance(eid,str) or eid in seen_events: raise RuntimeError("duplicate/invalid lifecycle event_id")
        seen_events.add(eid)
        if e.get("parent_event_sha256")!=parent: raise RuntimeError("authorization parent-event SHA lineage mismatch")
        et=parse_time(e.get("event_at_utc"),"event_at_utc")
        if last_time is not None and et<last_time: raise RuntimeError("authorization event time moved backwards")
        last_time=et
        typ=e.get("event_type")
        if typ not in proto["event_chain"]["allowed_event_types"]: raise RuntimeError("invalid lifecycle event_type")
        aid=e.get("authorization_id")
        pair=e.get("authorized_combination_id")
        if typ=="ISSUE":
            if active is not None: raise RuntimeError("ISSUE while an authorization is active")
            if not aid or aid in seen_auth: raise RuntimeError("duplicate/invalid authorization_id")
            seen_auth.add(aid)
            active={"authorization_id":aid,"authorization_sha256":e.get("authorization_sha256"),"authorized_combination_id":pair,"expires_at_utc":e.get("expires_at_utc"),"event_id":eid}
        elif typ=="SUPERSEDE":
            if active is None: raise RuntimeError("SUPERSEDE without active authorization")
            if e.get("supersedes_authorization_id")!=active["authorization_id"]: raise RuntimeError("SUPERSEDE target is not current authorization")
            if e.get("supersedes_authorization_sha256")!=active["authorization_sha256"]: raise RuntimeError("SUPERSEDE parent authorization SHA mismatch")
            if pair!=active["authorized_combination_id"]: raise RuntimeError("silent pair substitution detected")
            if not aid or aid in seen_auth or aid==active["authorization_id"]: raise RuntimeError("SUPERSEDE authorization_id invalid/duplicate")
            seen_auth.add(aid)
            active={"authorization_id":aid,"authorization_sha256":e.get("authorization_sha256"),"authorized_combination_id":pair,"expires_at_utc":e.get("expires_at_utc"),"event_id":eid}
        else:
            if active is None: raise RuntimeError("REVOKE without active authorization")
            if e.get("revokes_authorization_id")!=active["authorization_id"] or e.get("revokes_authorization_sha256")!=active["authorization_sha256"]:
                raise RuntimeError("REVOKE target is not current authorization")
            if not str(e.get("revocation_reason","")).strip(): raise RuntimeError("revocation reason missing")
            active=None
        history.append({"event_id":eid,"event_type":typ,"event_sha256":sha256_file(p),"authorization_id":aid})
        parent=sha256_file(p)
    usable=None;status="NONE"
    if active is not None:
        status="ACTIVE"
        if at_time is not None and at_time>=parse_time(active["expires_at_utc"],"active authorization expires_at_utc"):
            status="EXPIRED"
        else:
            usable=dict(active)
    return {
      "status":"PASS",
      "event_count":len(files),
      "last_event_sha256":parent,
      "active_authorization":active,
      "usable_current_authorization":usable,
      "current_status":status,
      "history":history,
      "selection_written":False,
      "production_state_mutated":False,
      "real_activation_authorized":False
    }

def request_binding(request:dict)->str:
    return canonical_sha256(request)

def build_event(request:dict,store_root:Path)->dict:
    proto=load(PROTO);exact_keys(request,EVENT_REQUEST_KEYS,"authorization lifecycle request")
    hits=forbidden_keys(request,set(proto["prohibited_keys"]))
    if hits: raise RuntimeError("authorization lifecycle request contains prohibited field: "+hits[0])
    if request.get("mode")!="SYNTHETIC" or request.get("synthetic_fixture") is not True: raise RuntimeError("authorization lifecycle is synthetic-only")
    eid=str(request.get("event_id",""))
    if not EVENT_ID_RE.fullmatch(eid): raise RuntimeError("synthetic lifecycle event_id invalid")
    typ=request.get("event_type")
    if typ not in proto["event_chain"]["allowed_event_types"]: raise RuntimeError("invalid lifecycle event_type")
    event_at=parse_time(request.get("event_at_utc"),"event_at_utc")
    validate_production_state()
    state=audit_chain(store_root,event_at)
    seq=state["event_count"]+1
    parent=state["last_event_sha256"]
    active=state["active_authorization"]
    base={
      "version":"1.0","artifact_class":"JNU_REDACTED_SYNTHETIC_AUTHORIZATION_LIFECYCLE_EVENT","storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,"mode":"SYNTHETIC","event_sequence":seq,"event_id":eid,"event_type":typ,
      "event_at_utc":request["event_at_utc"],"parent_event_sha256":parent,"request_binding_sha256":request_binding(request),
      "selection_write_permitted":False,"selection_written":False,"selected_combination_id":"UNSELECTED",
      "production_state_mutated":False,"real_activation_authorized":False
    }
    if typ in {"ISSUE","SUPERSEDE"}:
        if request.get("revocation_reason") is not None or request.get("revocation_authorizer_reference") is not None or request.get("revocation_authorizer_role") is not None or request.get("revocation_attestation") is not None:
            raise RuntimeError("revocation fields prohibited for ISSUE/SUPERSEDE")
        path=Path(str(request.get("authorization_path")))
        auth=validate_authorization_artifact(path,str(request.get("authorization_sha256","")),proto)
        a=auth["artifact"];aid=a["authorization_id"];pair=a["authorized_combination_id"]
        if event_at<auth["issued"]: raise RuntimeError("lifecycle event precedes authorization issuance")
        if event_at>=auth["expiry"]: raise RuntimeError("cannot ISSUE/SUPERSEDE expired authorization")
        if typ=="ISSUE":
            if active is not None: raise RuntimeError("ISSUE requires no active authorization")
            if request.get("target_authorization_id") is not None: raise RuntimeError("ISSUE target_authorization_id must be null")
        else:
            if active is None: raise RuntimeError("SUPERSEDE requires active authorization")
            if request.get("target_authorization_id")!=active["authorization_id"]: raise RuntimeError("SUPERSEDE target must be current authorization")
            if aid==active["authorization_id"]: raise RuntimeError("SUPERSEDE requires new authorization_id")
            if pair!=active["authorized_combination_id"]: raise RuntimeError("pair change requires explicit REVOKE then ISSUE")
            base["supersedes_authorization_id"]=active["authorization_id"]
            base["supersedes_authorization_sha256"]=active["authorization_sha256"]
        base.update({
          "authorization_id":aid,"authorization_sha256":auth["sha256"],"authorized_combination_id":pair,
          "review_batch_id":a["review_batch_id"],"review_receipt_sha256":a["review_receipt_sha256"],
          "composite_dossier_sha256":a["composite_dossier_sha256"],"expires_at_utc":a["expires_at_utc"],
          "authorizer_ref_sha256":hashlib.sha256(("authorizer:"+a["authorizer_reference"]).encode()).hexdigest(),
          "authorization_status":"SYNTHETIC_DISABLED"
        })
    else:
        if request.get("authorization_path") is not None or request.get("authorization_sha256") is not None:
            raise RuntimeError("REVOKE must not provide authorization artifact")
        if active is None: raise RuntimeError("REVOKE requires active authorization")
        if request.get("target_authorization_id")!=active["authorization_id"]: raise RuntimeError("REVOKE target must be current authorization")
        reason=str(request.get("revocation_reason","")).strip()
        if not reason: raise RuntimeError("revocation_reason required")
        if request.get("revocation_authorizer_role")!=proto["transition_rules"]["revocation_authorizer_role"]: raise RuntimeError("revocation authorizer role mismatch")
        if request.get("revocation_attestation")!=proto["transition_rules"]["revocation_attestation"]: raise RuntimeError("revocation attestation mismatch")
        ref=str(request.get("revocation_authorizer_reference",""))
        if not ref: raise RuntimeError("revocation authorizer reference required")
        base.update({
          "authorization_id":active["authorization_id"],"authorization_sha256":active["authorization_sha256"],
          "authorized_combination_id":active["authorized_combination_id"],
          "revokes_authorization_id":active["authorization_id"],"revokes_authorization_sha256":active["authorization_sha256"],
          "revocation_reason":reason,"revocation_authorizer_ref_sha256":hashlib.sha256(("revoker:"+ref).encode()).hexdigest(),
          "authorization_status_after_event":"REVOKED"
        })
    return base

def find_existing_event(store_root:Path,event_id:str)->Path|None:
    for p in event_files(store_root):
        e=load(p)
        if e.get("event_id")==event_id:return p
    return None

def process(request_path:Path,store_root:Path)->dict:
    require_external(request_path,"authorization lifecycle request")
    require_external(store_root,"authorization lifecycle store")
    if not request_path.is_file(): raise RuntimeError("authorization lifecycle request missing")
    request=load(request_path)
    existing=find_existing_event(store_root,str(request.get("event_id","")))
    if existing is not None:
        e=load(existing)
        if e.get("request_binding_sha256")!=request_binding(request): raise RuntimeError("same event_id reused with different request")
        audit=audit_chain(store_root,parse_time(request.get("event_at_utc"),"event_at_utc"))
        return {"status":"IDEMPOTENT_REPLAY_ACCEPTED","event_id":e["event_id"],"event_sha256":sha256_file(existing),"event_count":audit["event_count"],"current_status":audit["current_status"],"selection_written":False,"real_activation_authorized":False}
    event=build_event(request,store_root)
    target=store_root.resolve()/"authorization_events"/f"{event['event_sequence']:06d}_{event['event_id']}.json"
    result=write_immutable_json(store_root.resolve(),target,event)
    audit=audit_chain(store_root,parse_time(request.get("event_at_utc"),"event_at_utc"))
    return {"status":"AUTHORIZATION_LIFECYCLE_EVENT_WRITTEN","event_id":event["event_id"],"event_sha256":result["sha256"],"event_count":audit["event_count"],"current_status":audit["current_status"],"selection_written":False,"real_activation_authorized":False}

def validate_current_authorization(store_root:Path,authorization_id:str,authorization_sha256:str,at_time_utc:str)->dict:
    at=parse_time(at_time_utc,"at_time_utc")
    state=audit_chain(store_root,at)
    current=state["usable_current_authorization"]
    if current is None: raise RuntimeError("no usable current authorization")
    if current["authorization_id"]!=authorization_id: raise RuntimeError("authorization is stale, revoked, superseded, or not current")
    if current["authorization_sha256"]!=authorization_sha256: raise RuntimeError("current authorization SHA mismatch")
    return {"status":"CURRENT_SYNTHETIC_DISABLED_AUTHORIZATION_VALIDATED","authorization_id":authorization_id,"authorized_combination_id":current["authorized_combination_id"],"selection_write_permitted":False,"real_activation_authorized":False}

def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("apply");p.add_argument("--request",type=Path,required=True);p.add_argument("--store-root",type=Path,required=True)
    a=sub.add_parser("audit");a.add_argument("--store-root",type=Path,required=True);a.add_argument("--at-time-utc")
    v=sub.add_parser("validate-current");v.add_argument("--store-root",type=Path,required=True);v.add_argument("--authorization-id",required=True);v.add_argument("--authorization-sha256",required=True);v.add_argument("--at-time-utc",required=True)
    ns=ap.parse_args()
    if ns.cmd=="apply": out=process(ns.request,ns.store_root)
    elif ns.cmd=="audit": out=audit_chain(ns.store_root,parse_time(ns.at_time_utc,"at_time_utc") if ns.at_time_utc else None)
    else: out=validate_current_authorization(ns.store_root,ns.authorization_id,ns.authorization_sha256,ns.at_time_utc)
    print(json.dumps(out,indent=2))

if __name__=="__main__":main()
