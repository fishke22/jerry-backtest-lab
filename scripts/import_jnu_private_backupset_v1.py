from __future__ import annotations
import argparse,json,os,subprocess,sys
from pathlib import Path,PurePosixPath
from jnu_integrity_hash_v1 import canonical_text_sha256
from jnu_private_atomic_io_v1 import _atomic_bytes,require_external,sha256_file
from recover_jnu_private_entitled_ledger_v1 import scan
ROOT=Path(__file__).resolve().parents[1];FRAMEWORK=ROOT/"config"/"jnu_operational_framework_current_v1_9.json";SCORER=ROOT/"scripts"/"score_jnu_private_entitled_live_shadow_v1.py"
def safe_rel(s:str)->Path:
    p=PurePosixPath(s)
    if p.is_absolute() or ".." in p.parts or "." in p.parts:raise RuntimeError("backup manifest path traversal rejected")
    return Path(*p.parts)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--backupset",type=Path,required=True);ap.add_argument("--destination-ledger-root",type=Path,required=True);a=ap.parse_args()
    bs=a.backupset.resolve();dest=a.destination_ledger_root.resolve();require_external(bs,"private backup set");require_external(dest,"private DR destination")
    bm=json.loads((bs/"manifest.json").read_text(encoding="utf-8"))
    if bm.get("artifact_class")!="JNU_PRIVATE_BACKUP_SET" or bm.get("storage_scope")!="PRIVATE_INTERNAL_ONLY":raise RuntimeError("private backup set manifest invalid")
    if bm.get("framework_sha256")!=canonical_text_sha256(FRAMEWORK):raise RuntimeError("backup set framework SHA mismatch")
    if dest.exists() and any(dest.iterdir()):raise RuntimeError("DR import destination must be empty")
    checked=[]
    for e in bm.get("files",[]):
        rel=safe_rel(str(e["path"]));src=bs/"payload"/rel
        if not src.is_file():raise RuntimeError("backup payload file missing: "+str(rel))
        if src.stat().st_size!=int(e["size"]) or sha256_file(src)!=e["sha256"]:raise RuntimeError("backup payload integrity mismatch: "+str(rel))
        checked.append((rel,src))
    if len(checked)!=int(bm.get("file_count",-1)):raise RuntimeError("backup file count mismatch")
    dest.mkdir(parents=True,exist_ok=True)
    try:
        for rel,src in checked:_atomic_bytes(dest/rel,src.read_bytes(),mode=0o600,replace=False)
        rs=scan(dest,False)
        if rs["status"]!="PASS":raise RuntimeError("restored ledger recovery scan failed")
        out=dest/"results"/"dr_revalidated_v1.json"
        cp=subprocess.run([sys.executable,str(SCORER),"--private-ledger-root",str(dest),"--output",str(out)],cwd=ROOT,capture_output=True,text=True)
        if cp.returncode!=0:raise RuntimeError("restored ledger scorer revalidation failed: "+(cp.stderr or cp.stdout).strip())
    except Exception:
        raise
    print(json.dumps({"status":"PRIVATE_BACKUP_SET_IMPORTED_AND_REVALIDATED","backupset_id":bm["backupset_id"],"file_count":len(checked),"recovery_scan":"PASS","scorer_revalidation":"PASS","raw_private_data_printed":False,"public_output_created":False},indent=2))
if __name__=="__main__":main()
