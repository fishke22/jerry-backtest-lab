from __future__ import annotations
import argparse,json,re
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external
ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"config"/"jnu_private_launch_manifest_protocol_v1.json"
ID_RE=re.compile(r"^JNU_PRIV_LAUNCH_[A-Za-z0-9._-]{8,120}$")
def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict):raise RuntimeError("launch manifest must be an object")
    return x
def validate(x:dict)->dict:
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"));missing=[k for k in p["required_fields"] if k not in x]
    if missing:raise RuntimeError("missing launch manifest fields: "+",".join(missing))
    if not ID_RE.fullmatch(str(x["launch_id"])):raise RuntimeError("invalid launch_id")
    mode=x["mode"]
    if mode not in p["modes"]:raise RuntimeError("invalid launch mode")
    lr=Path(str(x["private_ledger_root"]));qr=Path(str(x["private_quote_store_root"]));require_external(lr,"private ledger root");require_external(qr,"private quote store root")
    if x["public_output_requested"] is not False:raise RuntimeError("private launch prohibits public output")
    if int(x["retention_days"])<=0:raise RuntimeError("retention_days must be positive")
    if mode=="SYNTHETIC":
        if x["synthetic_data_only"] is not True or x["real_entitlement_connected"] is not False:raise RuntimeError("synthetic launch flags invalid")
    else:
        if x["synthetic_data_only"] is not False or x["real_entitlement_connected"] is not True:raise RuntimeError("real launch flags invalid")
        if x.get("entitlement_status")!="EXPLICITLY_APPROVED":raise RuntimeError("real launch requires explicit entitlement approval")
        if x["retention_terms_status"]!="EXPLICITLY_CONFIRMED":raise RuntimeError("real launch requires confirmed retention terms")
    if x["cloud_processing_used"] is True and x["cloud_permission_status"]!="EXPLICITLY_APPROVED":raise RuntimeError("cloud processing requires explicit approval")
    if x["permanent_purge_allowed"] is True and x["retention_terms_status"]!="EXPLICITLY_CONFIRMED":raise RuntimeError("permanent purge requires confirmed retention terms")
    return {"version":"1.0","status":"PASS","launch_id":x["launch_id"],"mode":mode,"private_ledger_root":str(lr.resolve()),"private_quote_store_root":str(qr.resolve()),"public_output_requested":False}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--manifest",type=Path,required=True);a=ap.parse_args();x=load(a.manifest);print(json.dumps(validate(x),indent=2))
if __name__=="__main__":main()
