from __future__ import annotations
import hashlib, json, os, tempfile
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]

def require_external(p:Path,label:str="path")->None:
    rp=p.resolve();rr=ROOT.resolve()
    if rp==rr or rr in rp.parents:raise RuntimeError(f"{label} must resolve outside the public repository")

def json_bytes(obj:Any)->bytes:
    return (json.dumps(obj,ensure_ascii=False,indent=2)+"\n").encode("utf-8")

def sha256_bytes(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def sha256_file(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def _fsync_dir(p:Path)->None:
    try:
        fd=os.open(str(p),os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)
    except OSError:pass

def _atomic_bytes(path:Path,data:bytes,mode:int=0o600,replace:bool=True)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    if not replace and path.exists():raise FileExistsError(str(path))
    fd,tmp=tempfile.mkstemp(prefix=f".{path.name}.tmp-",dir=str(path.parent))
    tp=Path(tmp)
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        try:os.chmod(tp,mode)
        except OSError:pass
        if not replace and path.exists():raise FileExistsError(str(path))
        os.replace(tp,path);_fsync_dir(path.parent)
    finally:
        if tp.exists():
            try:tp.unlink()
            except OSError:pass

def backup_path(root:Path,target:Path)->Path:
    root=root.resolve();target=target.resolve();rel=target.relative_to(root)
    return root/"recovery"/"backups"/rel
def checksum_path(backup:Path)->Path:return Path(str(backup)+".sha256")

def verify_backup(root:Path,target:Path)->dict:
    b=backup_path(root,target);s=checksum_path(b)
    if not b.exists() or not s.exists():return {"status":"BACKUP_MISSING","backup":str(b)}
    expected=s.read_text(encoding="utf-8").strip()
    actual=sha256_file(b)
    if expected!=actual:return {"status":"BACKUP_CHECKSUM_INVALID","backup":str(b)}
    if target.exists():
        return {"status":"PASS" if sha256_file(target)==expected else "PRIMARY_MISMATCH","backup":str(b),"sha256":expected}
    return {"status":"PRIMARY_MISSING_BACKUP_VALID","backup":str(b),"sha256":expected}

def write_immutable_json(root:Path,target:Path,obj:Any)->dict:
    require_external(root,"private ledger root");require_external(target,"immutable target")
    root=root.resolve();target=target.resolve()
    data=json_bytes(obj);digest=sha256_bytes(data)
    lockdir=root/".locks";lockdir.mkdir(parents=True,exist_ok=True)
    lock=lockdir/(hashlib.sha256(str(target).encode()).hexdigest()+".lock")
    try:
        fd=os.open(str(lock),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    except FileExistsError:raise RuntimeError("private immutable record lock already exists; run recovery before retry")
    try:
        if target.exists():raise FileExistsError(str(target))
        b=backup_path(root,target);s=checksum_path(b)
        if b.exists() or s.exists():
            if not b.exists() or not s.exists():raise RuntimeError("partial private backup metadata detected; run recovery")
            if s.read_text(encoding="utf-8").strip()!=sha256_file(b):raise RuntimeError("private backup checksum invalid; run recovery")
            if sha256_file(b)!=digest:raise RuntimeError("existing private backup conflicts with intended immutable record")
        else:
            _atomic_bytes(b,data,replace=False);_atomic_bytes(s,(digest+"\n").encode(),replace=False)
        _atomic_bytes(target,data,replace=False)
        return {"status":"WRITTEN","sha256":digest,"backup":str(b)}
    finally:
        try:lock.unlink();_fsync_dir(lockdir)
        except OSError:pass

def write_replace_json(path:Path,obj:Any)->str:
    require_external(path,"private replace target");data=json_bytes(obj);_atomic_bytes(path.resolve(),data,replace=True);return sha256_bytes(data)

def restore_from_backup(root:Path,target:Path)->dict:
    v=verify_backup(root,target)
    if v["status"] not in {"PRIMARY_MISSING_BACKUP_VALID","PRIMARY_MISMATCH"}:raise RuntimeError("no checksum-verified backup available for restore")
    b=Path(v["backup"]);_atomic_bytes(target.resolve(),b.read_bytes(),replace=True)
    if verify_backup(root,target)["status"]!="PASS":raise RuntimeError("private restore verification failed")
    return {"status":"RESTORED"}
