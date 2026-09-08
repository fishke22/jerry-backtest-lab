from __future__ import annotations
import argparse,json,re
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external,write_replace_json
from jnu_private_lock_v1 import acquire_private_lock

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"config"/"jnu_private_restore_authorization_protocol_v1.json"
ID_RE=re.compile(r"^JNU_PRIV_RESTORE_[A-Za-z0-9._-]{8,120}$")

def dt(s):
    x=datetime.fromisoformat(str(s))
    if x.tzinfo is None:
        raise RuntimeError("restore authorization timestamps must be offset-aware")
    return x.astimezone(timezone.utc)

def load(path:Path)->dict:
    require_external(path,"private restore authorization")
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict):
        raise RuntimeError("restore authorization must be an object")
    return x

def validate(x:dict,backup_manifest:dict|None=None,now_utc:str|None=None)->dict:
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    missing=[k for k in p["required_fields"] if k not in x]
    if missing:
        raise RuntimeError("missing restore authorization fields: "+",".join(missing))
    if not ID_RE.fullmatch(str(x["restore_id"])):
        raise RuntimeError("invalid restore_id")
    dest=Path(str(x["destination_ledger_root"]))
    require_external(dest,"restore destination")
    if x["public_output_requested"] is not False:
        raise RuntimeError("private restore prohibits public output")
    if x["cloud_processing_used"] is True and x["cloud_permission_status"]!="EXPLICITLY_APPROVED":
        raise RuntimeError("cloud restore requires explicit permission")
    if x["single_use"] is not True:
        raise RuntimeError("restore authorization must be single-use")
    now=dt(now_utc) if now_utc else datetime.now(timezone.utc)
    if now<dt(x["authorized_at_utc"]) or now>dt(x["expires_at_utc"]):
        raise RuntimeError("restore authorization outside validity window")
    if x["mode"]=="SYNTHETIC":
        if x["authorization_status"]!="EXPLICITLY_APPROVED_SYNTHETIC" or x["real_entitlement_connected"] is not False:
            raise RuntimeError("synthetic restore authorization invalid")
        if x["restore_purpose"] not in p["allowed_synthetic_purposes"]:
            raise RuntimeError("synthetic restore purpose invalid")
    elif x["mode"]=="REAL_ENTITLED":
        if x["authorization_status"]!="EXPLICITLY_APPROVED_REAL" or x["real_entitlement_connected"] is not True:
            raise RuntimeError("real restore authorization invalid")
        raise RuntimeError("real entitled restore remains blocked pending external governance")
    else:
        raise RuntimeError("invalid restore authorization mode")
    if backup_manifest is not None:
        if x["backupset_id"]!=backup_manifest["backupset_id"]:
            raise RuntimeError("restore authorization backupset mismatch")
        if x["authorized_key_id"]!=backup_manifest["key_id"] or int(x["authorized_key_version"])!=int(backup_manifest["key_version"]):
            raise RuntimeError("restore authorization key binding mismatch")
    return {
      "version":"1.2","status":"PASS","restore_id":x["restore_id"],
      "backupset_id":x["backupset_id"],"authorized_key_id":x["authorized_key_id"],
      "authorized_key_version":x["authorized_key_version"],
      "destination_ledger_root":str(dest.resolve()),"single_use":True,
      "public_output_requested":False
    }

def authorization_usage_root(authorization_path:Path)->Path:
    require_external(authorization_path,"private restore authorization")
    root=authorization_path.resolve().parent/".restore_authorization_usage"
    require_external(root,"private restore authorization usage registry")
    return root

def authorization_usage_receipt_path(authorization_path:Path,restore_id:str)->Path:
    return authorization_usage_root(authorization_path)/"used"/f"{restore_id}.json"

@contextmanager
def authorization_use_guard(authorization_path:Path,restore_id:str):
    root=authorization_usage_root(authorization_path)
    root.mkdir(parents=True,exist_ok=True)
    with acquire_private_lock(root,"restore-auth:"+restore_id,lease_seconds=300,wait_seconds=5,break_stale=False):
        receipt=authorization_usage_receipt_path(authorization_path,restore_id)
        if receipt.exists():
            raise RuntimeError("RESTORE_AUTHORIZATION_ALREADY_USED")
        yield receipt

def mark_authorization_used(receipt_path:Path,av:dict,backup_manifest:dict)->None:
    write_replace_json(receipt_path,{
      "version":"1.0",
      "artifact_class":"JNU_PRIVATE_RESTORE_AUTHORIZATION_USAGE",
      "storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,
      "restore_id":av["restore_id"],
      "backupset_id":backup_manifest["backupset_id"],
      "authorized_key_id":av["authorized_key_id"],
      "authorized_key_version":av["authorized_key_version"],
      "destination_ledger_root":av["destination_ledger_root"],
      "status":"SUCCESSFULLY_CONSUMED",
      "successful_restore_consumes_authorization":True
    })

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--authorization",type=Path,required=True)
    ap.add_argument("--backup-manifest",type=Path)
    ap.add_argument("--now-utc")
    a=ap.parse_args()
    bm=json.loads(a.backup_manifest.read_text()) if a.backup_manifest else None
    print(json.dumps(validate(load(a.authorization),bm,a.now_utc),indent=2))

if __name__=="__main__":
    main()
