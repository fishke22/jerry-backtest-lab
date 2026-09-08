from __future__ import annotations
import argparse,json,os,shutil,uuid
from datetime import datetime,timezone
from pathlib import Path
from jnu_integrity_hash_v1 import canonical_text_sha256
from jnu_private_atomic_io_v1 import require_external,sha256_file
from jnu_private_lock_v1 import acquire_private_lock
from recover_jnu_private_entitled_ledger_v1 import scan
from validate_jnu_private_launch_manifest_v1 import load as load_manifest,validate as validate_manifest
ROOT=Path(__file__).resolve().parents[1];FRAMEWORK=ROOT/"config"/"jnu_operational_framework_current_v1_9.json"
INCLUDE={"forecasts","outcomes","recovery","results","launch_states","retention_quarantine"}
def safe_rel(p:Path,root:Path)->str:
    rel=p.resolve().relative_to(root.resolve())
    if rel.is_absolute() or ".." in rel.parts:raise RuntimeError("unsafe backup relative path")
    return rel.as_posix()
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--manifest",type=Path,required=True);ap.add_argument("--destination-root",type=Path,required=True);ap.add_argument("--backupset-id");a=ap.parse_args()
    m=load_manifest(a.manifest);v=validate_manifest(m)
    if m["mode"]!="SYNTHETIC":raise RuntimeError("real entitled backup export prohibited until encryption/key-management/provider terms are resolved")
    root=Path(v["private_ledger_root"]).resolve();destroot=a.destination_root.resolve();require_external(destroot,"private backup destination")
    if root==destroot or root in destroot.parents or destroot in root.parents:raise RuntimeError("backup destination must be separate from ledger root")
    bid=a.backupset_id or ("JNU_PRIV_BACKUP_"+uuid.uuid4().hex);out=destroot/bid
    if out.exists():raise RuntimeError("backup set destination already exists")
    with acquire_private_lock(root,"backupset-export",lease_seconds=300,wait_seconds=5):
        rs=scan(root,False)
        if rs["status"]!="PASS":raise RuntimeError("ledger recovery scan must PASS before backup export")
        files=[]
        for top in INCLUDE:
            base=root/top
            if not base.exists():continue
            for p in sorted(base.rglob("*")):
                if not p.is_file():continue
                rel=safe_rel(p,root)
                if "/quarantine/temp/" in ("/"+rel+"/"):continue
                files.append((rel,p))
        tmp=destroot/("."+bid+".tmp-"+uuid.uuid4().hex);payload=tmp/"payload";payload.mkdir(parents=True)
        try:
            entries=[]
            for rel,p in files:
                d=payload/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d)
                try:os.chmod(d,0o600)
                except OSError:pass
                entries.append({"path":rel,"sha256":sha256_file(d),"size":d.stat().st_size})
            bm={"version":"1.0","artifact_class":"JNU_PRIVATE_BACKUP_SET","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"backupset_id":bid,"created_at_utc":datetime.now(timezone.utc).isoformat(),"source_launch_id":m["launch_id"],"framework_sha256":canonical_text_sha256(FRAMEWORK),"file_count":len(entries),"files":entries}
            (tmp/"manifest.json").write_text(json.dumps(bm,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            try:os.chmod(tmp/"manifest.json",0o600);os.chmod(tmp,0o700);os.chmod(payload,0o700)
            except OSError:pass
            os.replace(tmp,out)
        finally:
            if tmp.exists():shutil.rmtree(tmp)
    print(json.dumps({"status":"PRIVATE_BACKUP_SET_EXPORTED","backupset_id":bid,"file_count":len(files),"raw_private_data_printed":False,"public_output_created":False},indent=2))
if __name__=="__main__":main()
