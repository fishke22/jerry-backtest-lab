from __future__ import annotations
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external,write_replace_json
from jnu_private_lock_v1 import acquire_private_lock
from validate_jnu_private_launch_manifest_v1 import load as load_manifest,validate as validate_manifest

STATES=["PREPARED","QUOTE_BOUND","FORECASTED","OUTCOME_PENDING","OUTCOME_RECORDED","SCORED"]
def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict):raise RuntimeError(f"{p} must contain an object")
    return x
def reconcile(manifest_path:Path,request_path:Path,quote_path:Path|None=None)->dict:
    m=load_manifest(manifest_path);v=validate_manifest(m);root=Path(v["private_ledger_root"]);require_external(root,"private ledger root")
    req=load(request_path);rid=str(req["request_id"]);fid="JNU_PRIV_LS_"+hashlib.sha256(rid.encode()).hexdigest()[:24]
    forecast=root/"forecasts"/f"{fid}.json";outcome=root/"outcomes"/f"{fid}.json";scorecp=root/"results"/"private_live_shadow_checkpoint_v1.json"
    quote_receipt=None
    if quote_path is not None:
        require_external(quote_path,"private quote bundle");q=load(quote_path)
        if q.get("artifact_class")!="JNU_PRIVATE_ENTITLED_QUOTE_BUNDLE":raise RuntimeError("quote bundle class invalid")
        quote_receipt=q.get("receipt_id")
    if outcome.exists() and not forecast.exists():raise RuntimeError("STATE_MACHINE_ORPHAN_OUTCOME")
    if scorecp.exists() and not outcome.exists():raise RuntimeError("STATE_MACHINE_SCORE_WITHOUT_OUTCOME")
    targets=["PREPARED"]
    if quote_receipt or forecast.exists():targets.append("QUOTE_BOUND")
    if forecast.exists():targets.extend(["FORECASTED","OUTCOME_PENDING"])
    if outcome.exists():targets.append("OUTCOME_RECORDED")
    if scorecp.exists():targets.append("SCORED")
    target=targets[-1];sp=root/"launch_states"/f"{m['launch_id']}.json";now=datetime.now(timezone.utc).isoformat()
    with acquire_private_lock(root,"launch-state:"+m["launch_id"],lease_seconds=120,wait_seconds=5):
        if sp.exists():
            state=load(sp);cur=state["current_state"]
            if STATES.index(cur)>STATES.index(target):raise RuntimeError("STATE_MACHINE_REGRESSION")
            history=list(state.get("history",[]))
        else:
            history=[];state={"version":"1.0","artifact_class":"JNU_PRIVATE_LAUNCH_STATE","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"launch_id":m["launch_id"],"request_id":rid,"forecast_id":fid}
        seen=[h["state"] for h in history]
        for st in targets:
            if st not in seen:
                history.append({"state":st,"at_utc":now,"reconstructed":sp.exists() is False and len(seen)==0 and st!="PREPARED"});seen.append(st)
        state["current_state"]=target;state["history"]=history;state["quote_receipt_id"]=quote_receipt or state.get("quote_receipt_id");state["updated_at_utc"]=now
        write_replace_json(sp,state)
    return {"status":"PASS","launch_id":m["launch_id"],"current_state":target,"forecast_id":fid,"public_output_created":False}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--manifest",type=Path,required=True);ap.add_argument("--request",type=Path,required=True);ap.add_argument("--private-quote-bundle",type=Path);a=ap.parse_args()
    print(json.dumps(reconcile(a.manifest,a.request,a.private_quote_bundle),indent=2))
if __name__=="__main__":main()
