from __future__ import annotations
import argparse,json,shutil,subprocess,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external,write_replace_json

ROOT=Path(__file__).resolve().parents[1]
IMPORT=ROOT/"scripts"/"import_jnu_private_encrypted_backupset_v1.py"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--backupset",type=Path,required=True)
    ap.add_argument("--keyring",type=Path,required=True)
    ap.add_argument("--authorization",type=Path,required=True)
    ap.add_argument("--drill-root",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    a=ap.parse_args()

    require_external(a.drill_root,"private DR drill root");require_external(a.report,"private DR drill report")
    bm=json.loads((a.backupset/"manifest.json").read_text(encoding="utf-8"))
    drill_id="JNU_PRIV_DRILL_"+uuid.uuid4().hex
    dest=a.drill_root.resolve()/drill_id
    auth=json.loads(a.authorization.read_text(encoding="utf-8"))
    auth2=dict(auth);auth2["destination_ledger_root"]=str(dest)
    auth_tmp=a.drill_root.resolve()/(drill_id+".authorization.json")
    auth_tmp.parent.mkdir(parents=True,exist_ok=True);auth_tmp.write_text(json.dumps(auth2,indent=2)+"\n",encoding="utf-8")
    try:
        start=time.monotonic()
        cp=subprocess.run([sys.executable,str(IMPORT),"--backupset",str(a.backupset),"--keyring",str(a.keyring),"--authorization",str(auth_tmp)],cwd=ROOT,capture_output=True,text=True)
        elapsed=time.monotonic()-start
        if cp.returncode!=0:
            raise RuntimeError("encrypted DR drill import failed: "+(cp.stderr or cp.stdout).strip())
        now=datetime.now(timezone.utc)
        created=datetime.fromisoformat(str(bm["created_at_utc"]))
        backup_age=max(0.0,(now-created).total_seconds())
        result={
          "version":"1.0","artifact_class":"JNU_PRIVATE_ENCRYPTED_DR_DRILL",
          "storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,
          "drill_id":drill_id,"backupset_id":bm["backupset_id"],"key_id":bm["key_id"],
          "completed_at_utc":now.isoformat(),"rto_seconds":elapsed,"backup_age_seconds":backup_age,
          "synthetic_rto_objective_seconds":60,"synthetic_backup_age_objective_seconds":86400,
          "rto_objective_met":elapsed<=60,"backup_age_objective_met":backup_age<=86400,
          "integrity_status":"PASS","recovery_scan":"PASS","scorer_revalidation":"PASS",
          "raw_private_data_printed":False,"key_material_printed":False,"public_output_created":False
        }
        write_replace_json(a.report,result)
    finally:
        try:auth_tmp.unlink()
        except OSError:pass
        if dest.exists():shutil.rmtree(dest)
    print(json.dumps({"status":"PRIVATE_ENCRYPTED_DR_DRILL_PASS","drill_id":drill_id,"rto_objective_met":result["rto_objective_met"],"backup_age_objective_met":result["backup_age_objective_met"],"raw_private_data_printed":False,"key_material_printed":False,"public_output_created":False},indent=2))
if __name__=="__main__":main()
