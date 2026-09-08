from __future__ import annotations
import argparse,json,shutil,subprocess,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external,write_replace_json
from validate_jnu_private_restore_authorization_v1 import load as load_auth,validate as validate_auth
ROOT=Path(__file__).resolve().parents[1];IMPORT=ROOT/"scripts"/"import_jnu_private_encrypted_backupset_v1.py"
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--backupset",type=Path,required=True);ap.add_argument("--keyring",type=Path,required=True);ap.add_argument("--authorization",type=Path,required=True);ap.add_argument("--drill-root",type=Path,required=True);ap.add_argument("--drill-id",required=True);ap.add_argument("--report",type=Path,required=True);ap.add_argument("--rpo-objective-seconds",type=float,default=86400);ap.add_argument("--rto-objective-seconds",type=float,default=60);ap.add_argument("--now-utc");a=ap.parse_args()
    require_external(a.drill_root,"private DR drill root");require_external(a.report,"private DR drill report")
    bm=json.loads((a.backupset/"manifest.json").read_text(encoding="utf-8"));dest=a.drill_root.resolve()/a.drill_id
    av=validate_auth(load_auth(a.authorization),bm,a.now_utc)
    if Path(av["destination_ledger_root"]).resolve()!=dest:raise RuntimeError("DR drill authorization destination must equal drill destination")
    now=datetime.fromisoformat(a.now_utc).astimezone(timezone.utc) if a.now_utc else datetime.now(timezone.utc);src=datetime.fromisoformat(str(bm["source_latest_record_mtime_utc"])).astimezone(timezone.utc);rpo=max(0.0,(now-src).total_seconds())
    start=time.monotonic();cmd=[sys.executable,str(IMPORT),"--backupset",str(a.backupset),"--keyring",str(a.keyring),"--authorization",str(a.authorization)]
    if a.now_utc:cmd+=["--now-utc",a.now_utc]
    cp=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);elapsed=time.monotonic()-start
    restore_pass=cp.returncode==0;rpo_pass=rpo<=a.rpo_objective_seconds;rto_pass=elapsed<=a.rto_objective_seconds
    result={"version":"1.1","artifact_class":"JNU_PRIVATE_ENCRYPTED_DR_DRILL","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"drill_id":a.drill_id,"restore_id":av["restore_id"],"backupset_id":bm["backupset_id"],"key_id":bm["key_id"],"key_version":bm["key_version"],"completed_at_utc":now.isoformat(),"rto_seconds":elapsed,"rpo_seconds":rpo,"rto_objective_seconds":a.rto_objective_seconds,"rpo_objective_seconds":a.rpo_objective_seconds,"rto_objective_met":rto_pass,"rpo_objective_met":rpo_pass,"restore_pass":restore_pass,"overall_pass":restore_pass and rpo_pass and rto_pass,"raw_private_data_printed":False,"key_material_printed":False,"public_output_created":False}
    write_replace_json(a.report,result)
    if dest.exists():shutil.rmtree(dest)
    print(json.dumps({"status":"PRIVATE_ENCRYPTED_DR_DRILL_PASS" if result["overall_pass"] else "PRIVATE_ENCRYPTED_DR_DRILL_FAIL","drill_id":a.drill_id,"restore_pass":restore_pass,"rto_objective_met":rto_pass,"rpo_objective_met":rpo_pass,"raw_private_data_printed":False,"key_material_printed":False,"public_output_created":False},indent=2))
    raise SystemExit(0 if result["overall_pass"] else 7)
if __name__=="__main__":main()
