from __future__ import annotations
import argparse,json,os,uuid
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--backup-root",type=Path,required=True)
    ap.add_argument("--keep-generations",type=int,default=3)
    ap.add_argument("--apply",action="store_true")
    a=ap.parse_args()
    root=a.backup_root.resolve();require_external(root,"private encrypted backup root")
    if a.keep_generations<1:
        raise RuntimeError("keep-generations must be >=1")
    sets=[]
    for d in root.iterdir() if root.exists() else []:
        if not d.is_dir() or not d.name.startswith("JNU_PRIV_EBACKUP_"):continue
        mp=d/"manifest.json"
        if not mp.exists():raise RuntimeError("encrypted backup generation missing manifest")
        m=json.loads(mp.read_text(encoding="utf-8"))
        sets.append((m["created_at_utc"],d,m["backupset_id"]))
    sets.sort(reverse=True)
    old=sets[a.keep_generations:]
    moved=0
    if a.apply:
        q=root/"rotation_quarantine";q.mkdir(parents=True,exist_ok=True)
        for _,d,bid in old:
            dest=q/(bid+"-"+uuid.uuid4().hex[:8])
            os.replace(d,dest);moved+=1
    print(json.dumps({"status":"PASS","active_generations":min(len(sets),a.keep_generations),"eligible_old_generations":len(old),"quarantined_generations":moved,"permanent_delete_performed":False},indent=2))
if __name__=="__main__":main()
