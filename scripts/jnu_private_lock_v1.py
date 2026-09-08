from __future__ import annotations
import argparse,hashlib,json,os,socket,time,uuid
from contextlib import contextmanager
from datetime import datetime,timezone,timedelta
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external

def _now():return datetime.now(timezone.utc)
def lock_path(root:Path,key:str)->Path:
    return root.resolve()/".locks"/(hashlib.sha256(key.encode()).hexdigest()+".json")
def read_lock(path:Path)->dict:
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return {"invalid":True}
def is_stale(meta:dict,now=None)->bool:
    if meta.get("invalid") is True:return False
    try:
        exp=datetime.fromisoformat(str(meta["lease_expires_at_utc"]))
        if exp.tzinfo is None:return False
        return (now or _now())>=exp
    except Exception:return False
def quarantine_stale(root:Path,path:Path)->Path:
    q=root.resolve()/"recovery"/"quarantine"/"stale_locks";q.mkdir(parents=True,exist_ok=True)
    dest=q/(path.stem+"-"+uuid.uuid4().hex+".json")
    os.replace(path,dest)
    return dest

@contextmanager
def acquire_private_lock(root:Path,key:str,lease_seconds:int=120,wait_seconds:float=5.0,break_stale:bool=False):
    require_external(root,"private lock root");root=root.resolve();ld=root/".locks";ld.mkdir(parents=True,exist_ok=True)
    p=lock_path(root,key);token=uuid.uuid4().hex;deadline=time.monotonic()+max(0.0,float(wait_seconds))
    while True:
        now=_now();meta={"version":"1.0","owner_token":token,"pid":os.getpid(),"hostname":socket.gethostname(),"acquired_at_utc":now.isoformat(),"lease_expires_at_utc":(now+timedelta(seconds=int(lease_seconds))).isoformat(),"key_sha256":hashlib.sha256(key.encode()).hexdigest()}
        try:
            fd=os.open(str(p),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            with os.fdopen(fd,"w",encoding="utf-8") as f:json.dump(meta,f,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
            break
        except FileExistsError:
            existing=read_lock(p)
            if is_stale(existing):
                if break_stale:
                    try:quarantine_stale(root,p)
                    except FileNotFoundError:pass
                    continue
                raise RuntimeError("PRIVATE_LOCK_STALE_REQUIRES_RECOVERY")
            if time.monotonic()>=deadline:raise RuntimeError("PRIVATE_LOCK_BUSY")
            time.sleep(0.05)
    try:
        yield meta
    finally:
        try:
            current=read_lock(p)
            if current.get("owner_token")==token:p.unlink()
        except FileNotFoundError:pass

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True);ap.add_argument("--key",required=True);ap.add_argument("--hold-seconds",type=float,default=0);ap.add_argument("--lease-seconds",type=int,default=120);ap.add_argument("--wait-seconds",type=float,default=0);ap.add_argument("--break-stale",action="store_true");a=ap.parse_args()
    with acquire_private_lock(a.root,a.key,a.lease_seconds,a.wait_seconds,a.break_stale):
        if a.hold_seconds>0:time.sleep(a.hold_seconds)
        print(json.dumps({"status":"PRIVATE_LOCK_ACQUIRED","raw_private_data_printed":False},indent=2))
if __name__=="__main__":main()
