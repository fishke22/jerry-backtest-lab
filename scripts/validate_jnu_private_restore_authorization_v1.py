from __future__ import annotations
import argparse,json,re
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"config"/"jnu_private_restore_authorization_protocol_v1.json"
ID_RE=re.compile(r"^JNU_PRIV_RESTORE_[A-Za-z0-9._-]{8,120}$")

def load(path:Path)->dict:
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict):
        raise RuntimeError("restore authorization must be an object")
    return x

def validate(x:dict)->dict:
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
    if x["mode"]=="SYNTHETIC":
        if x["authorization_status"]!="EXPLICITLY_APPROVED_SYNTHETIC" or x["real_entitlement_connected"] is not False:
            raise RuntimeError("synthetic restore authorization invalid")
    elif x["mode"]=="REAL_ENTITLED":
        if x["authorization_status"]!="EXPLICITLY_APPROVED_REAL" or x["real_entitlement_connected"] is not True:
            raise RuntimeError("real restore authorization invalid")
        raise RuntimeError("real entitled restore remains blocked pending external governance")
    else:
        raise RuntimeError("invalid restore authorization mode")
    if not str(x["backupset_id"]).startswith("JNU_PRIV_EBACKUP_"):
        raise RuntimeError("invalid encrypted backupset id")
    if not str(x["authorized_key_id"]).startswith("JNU_KEY_"):
        raise RuntimeError("invalid authorized_key_id")
    return {"version":"1.0","status":"PASS","restore_id":x["restore_id"],"backupset_id":x["backupset_id"],"authorized_key_id":x["authorized_key_id"],"destination_ledger_root":str(dest.resolve()),"public_output_requested":False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--authorization",type=Path,required=True);a=ap.parse_args()
    print(json.dumps(validate(load(a.authorization)),indent=2))
if __name__=="__main__":main()
