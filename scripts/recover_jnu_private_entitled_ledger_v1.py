from __future__ import annotations
import argparse,json,os,shutil
from pathlib import Path
from jnu_private_atomic_io_v1 import backup_path,checksum_path,require_external,restore_from_backup,verify_backup
from jnu_private_lock_v1 import acquire_private_lock,is_stale,read_lock,quarantine_stale
from validate_jnu_private_launch_manifest_v1 import load as load_manifest,validate as validate_manifest

def scan(root:Path,apply:bool,ignore_owner_token:str|None=None)->dict:
    root=root.resolve();require_external(root,"private ledger root");recoverable=[];fatal=[];restored=0;quarantined_tmp=0
    for kind in ["forecasts","outcomes"]:
        d=root/kind
        for p in sorted(d.glob("*.json")) if d.exists() else []:
            v=verify_backup(root,p)
            if v["status"]=="PASS":continue
            if v["status"] in {"PRIMARY_MISMATCH"}:recoverable.append((p,v["status"]))
            else:fatal.append((p,v["status"]))
    broot=root/"recovery"/"backups"
    for kind in ["forecasts","outcomes"]:
        bd=broot/kind
        for b in sorted(bd.glob("*.json")) if bd.exists() else []:
            primary=root/kind/b.name
            if not primary.exists():
                v=verify_backup(root,primary)
                if v["status"]=="PRIMARY_MISSING_BACKUP_VALID":recoverable.append((primary,v["status"]))
                elif v["status"]!="PASS":fatal.append((primary,v["status"]))
    fd=root/"forecasts";od=root/"outcomes";fids={p.stem for p in fd.glob("*.json")} if fd.exists() else set();oids={p.stem for p in od.glob("*.json")} if od.exists() else set()
    orphan=sorted(oids-fids)
    if orphan:fatal.append((root/"outcomes","ORPHAN_OUTCOME"))
    pending=len(fids-oids)
    stale_locks=[];active_locks=[]
    ld=root/".locks"
    for lp in sorted(ld.glob("*.json")) if ld.exists() else []:
        meta=read_lock(lp)
        if ignore_owner_token and meta.get("owner_token")==ignore_owner_token:continue
        if is_stale(meta):stale_locks.append(lp)
        else:active_locks.append(lp)
    if active_locks:fatal.append((ld,"ACTIVE_PRIVATE_LOCK_PRESENT"))
    for lp in stale_locks:recoverable.append((lp,"STALE_PRIVATE_LOCK"))
    if apply and fatal:raise RuntimeError("private recovery cannot apply while fatal corruption exists")
    if apply:
        seen=set()
        for p,reason in recoverable:
            key=str(p.resolve())
            if key in seen:continue
            seen.add(key)
            if reason=="STALE_PRIVATE_LOCK":
                if p.exists():quarantine_stale(root,p)
            else:
                restore_from_backup(root,p);restored+=1
        q=root/"recovery"/"quarantine"/"temp";q.mkdir(parents=True,exist_ok=True)
        for p in list(root.rglob(".*.tmp-*")):
            if q in p.parents:continue
            dest=q/p.name
            if dest.exists():dest=q/(p.name+"-"+str(quarantined_tmp))
            os.replace(p,dest);quarantined_tmp+=1
    status="FATAL_CORRUPTION" if fatal else ("RECOVERY_REQUIRED" if recoverable and not apply else "PASS")
    return {"status":status,"recoverable_count":len({str(x[0]) for x in recoverable}),"fatal_count":len(fatal),"restored_count":restored,"pending_outcome_count":pending,"temp_quarantined_count":quarantined_tmp,"stale_lock_count":len(stale_locks),"active_lock_count":len(active_locks)}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--manifest",type=Path,required=True);ap.add_argument("--apply",action="store_true");a=ap.parse_args()
    m=load_manifest(a.manifest);v=validate_manifest(m)
    if a.apply and m["recovery_apply_allowed"] is not True:raise RuntimeError("launch manifest prohibits recovery apply")
    root=Path(v["private_ledger_root"])
    with acquire_private_lock(root,"ledger-mutation",lease_seconds=300,wait_seconds=5,break_stale=False) as lm:
        r=scan(root,a.apply,ignore_owner_token=lm["owner_token"])
    print(json.dumps(r,indent=2))
    raise SystemExit(0 if r["status"]=="PASS" else (4 if r["status"]=="RECOVERY_REQUIRED" else 5))
if __name__=="__main__":main()
