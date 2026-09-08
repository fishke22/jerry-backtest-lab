from __future__ import annotations
import argparse,json,re
from datetime import datetime,timezone
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external
ROOT=Path(__file__).resolve().parents[1];PROTOCOL=ROOT/"config"/"jnu_private_restore_authorization_protocol_v1.json";ID_RE=re.compile(r"^JNU_PRIV_RESTORE_[A-Za-z0-9._-]{8,120}$")
def dt(s):
    x=datetime.fromisoformat(str(s))
    if x.tzinfo is None:raise RuntimeError("restore authorization timestamps must be offset-aware")
    return x.astimezone(timezone.utc)
def load(path:Path)->dict:
    require_external(path,"private restore authorization");x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict):raise RuntimeError("restore authorization must be an object")
    return x
def validate(x:dict,backup_manifest:dict|None=None,now_utc:str|None=None)->dict:
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"));missing=[k for k in p["required_fields"] if k not in x]
    if missing:raise RuntimeError("missing restore authorization fields: "+",".join(missing))
    if not ID_RE.fullmatch(str(x["restore_id"])):raise RuntimeError("invalid restore_id")
    dest=Path(str(x["destination_ledger_root"]));require_external(dest,"restore destination")
    if x["public_output_requested"] is not False:raise RuntimeError("private restore prohibits public output")
    if x["cloud_processing_used"] is True and x["cloud_permission_status"]!="EXPLICITLY_APPROVED":raise RuntimeError("cloud restore requires explicit permission")
    if x["single_use"] is not True:raise RuntimeError("restore authorization must be single-use")
    now=dt(now_utc) if now_utc else datetime.now(timezone.utc)
    if now<dt(x["authorized_at_utc"]) or now>dt(x["expires_at_utc"]):raise RuntimeError("restore authorization outside validity window")
    if x["mode"]=="SYNTHETIC":
        if x["authorization_status"]!="EXPLICITLY_APPROVED_SYNTHETIC" or x["real_entitlement_connected"] is not False:raise RuntimeError("synthetic restore authorization invalid")
        if x["restore_purpose"] not in p["allowed_synthetic_purposes"]:raise RuntimeError("synthetic restore purpose invalid")
    elif x["mode"]=="REAL_ENTITLED":
        if x["authorization_status"]!="EXPLICITLY_APPROVED_REAL" or x["real_entitlement_connected"] is not True:raise RuntimeError("real restore authorization invalid")
        raise RuntimeError("real entitled restore remains blocked pending external governance")
    else:raise RuntimeError("invalid restore authorization mode")
    if backup_manifest is not None:
        if x["backupset_id"]!=backup_manifest["backupset_id"]:raise RuntimeError("restore authorization backupset mismatch")
        if x["authorized_key_id"]!=backup_manifest["key_id"] or int(x["authorized_key_version"])!=int(backup_manifest["key_version"]):raise RuntimeError("restore authorization key binding mismatch")
    return {"version":"1.1","status":"PASS","restore_id":x["restore_id"],"backupset_id":x["backupset_id"],"authorized_key_id":x["authorized_key_id"],"authorized_key_version":x["authorized_key_version"],"destination_ledger_root":str(dest.resolve()),"single_use":True,"public_output_requested":False}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--authorization",type=Path,required=True);ap.add_argument("--backup-manifest",type=Path);ap.add_argument("--now-utc");a=ap.parse_args();bm=json.loads(a.backup_manifest.read_text()) if a.backup_manifest else None;print(json.dumps(validate(load(a.authorization),bm,a.now_utc),indent=2))
if __name__=="__main__":main()
