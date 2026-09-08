from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
from validate_jnu_private_launch_manifest_v1 import load,validate
ROOT=Path(__file__).resolve().parents[1];REG=ROOT/"scripts"/"register_jnu_private_entitled_forecast_v1.py";STATE=ROOT/"scripts"/"jnu_private_launch_state_v1.py"
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--manifest",type=Path,required=True);ap.add_argument("--request",type=Path,required=True);ap.add_argument("--private-quote-bundle",type=Path,required=True);ap.add_argument("--created-at-taipei");a=ap.parse_args()
    v=validate(load(a.manifest));cmd=[sys.executable,str(REG),"--request",str(a.request),"--private-quote-bundle",str(a.private_quote_bundle),"--private-ledger-root",v["private_ledger_root"]]
    if a.created_at_taipei:cmd+=["--created-at-taipei",a.created_at_taipei]
    cp=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    if cp.returncode!=0:raise RuntimeError("private launch registrar fail-closed: "+(cp.stderr or cp.stdout).strip())
    r=json.loads(cp.stdout)
    sp=subprocess.run([sys.executable,str(STATE),"--manifest",str(a.manifest),"--request",str(a.request),"--private-quote-bundle",str(a.private_quote_bundle)],cwd=ROOT,capture_output=True,text=True)
    if sp.returncode!=0:raise RuntimeError("private launch state reconciliation fail-closed: "+(sp.stderr or sp.stdout).strip())
    sr=json.loads(sp.stdout)
    print(json.dumps({"status":"PRIVATE_LAUNCH_FORECAST_READY","registration_status":r["status"],"forecast_id":r["forecast_id"],"launch_state":sr["current_state"],"raw_and_derived_fields_not_printed":True,"public_output_created":False},indent=2))
if __name__=="__main__":main()
