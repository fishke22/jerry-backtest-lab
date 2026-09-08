from __future__ import annotations
import argparse,base64,json,os,re,secrets,uuid
from datetime import datetime,timezone
from pathlib import Path
from jnu_private_atomic_io_v1 import _atomic_bytes,require_external
from jnu_private_lock_v1 import acquire_private_lock

KEY_ID_RE=re.compile(r"^JNU_KEY_[A-Za-z0-9._-]{6,120}$")

def _load(path:Path)->dict:
    require_external(path,"private keyring")
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict) or x.get("artifact_class")!="JNU_PRIVATE_KEYRING":
        raise RuntimeError("private keyring artifact invalid")
    _check_mode(path)
    keys=x.get("keys")
    if not isinstance(keys,list) or not keys:
        raise RuntimeError("private keyring keys missing")
    active=[k for k in keys if k.get("status")=="ACTIVE"]
    if len(active)!=1:
        raise RuntimeError("private keyring must contain exactly one ACTIVE key")
    for k in keys:
        raw=base64.b64decode(str(k.get("material_b64","")),validate=True)
        if len(raw)!=32:
            raise RuntimeError("private key material must be 32 bytes")
    return x

def _check_mode(path:Path)->None:
    if os.name!="nt":
        mode=path.stat().st_mode & 0o777
        if mode & 0o077:
            raise RuntimeError("private keyring permissions must be 0600 or stricter")

def _write(path:Path,obj:dict)->None:
    require_external(path,"private keyring")
    data=(json.dumps(obj,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    _atomic_bytes(path.resolve(),data,mode=0o600,replace=True)
    _check_mode(path)

def _new_key(key_id:str,version:int)->dict:
    if not KEY_ID_RE.fullmatch(key_id):
        raise RuntimeError("invalid key_id")
    return {
      "key_id":key_id,
      "key_version":int(version),
      "algorithm":"AES-256-GCM",
      "status":"ACTIVE",
      "created_at_utc":datetime.now(timezone.utc).isoformat(),
      "material_b64":base64.b64encode(secrets.token_bytes(32)).decode("ascii")
    }

def init_keyring(path:Path,key_id:str)->dict:
    require_external(path,"private keyring")
    if path.exists():
        raise RuntimeError("private keyring already exists")
    obj={"version":"1.0","artifact_class":"JNU_PRIVATE_KEYRING","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"active_key_id":key_id,"keys":[_new_key(key_id,1)]}
    _write(path,obj)
    return {"status":"PRIVATE_KEYRING_INITIALIZED","active_key_id":key_id,"key_version":1,"key_material_printed":False}

def rotate_keyring(path:Path,new_key_id:str)->dict:
    root=path.resolve().parent
    require_external(root,"private keyring directory")
    with acquire_private_lock(root,"keyring:"+path.name,lease_seconds=120,wait_seconds=5):
        x=_load(path)
        if any(k.get("key_id")==new_key_id for k in x["keys"]):
            raise RuntimeError("new key_id already exists")
        maxv=max(int(k["key_version"]) for k in x["keys"])
        for k in x["keys"]:
            if k.get("status")=="ACTIVE":
                k["status"]="RETIRED"
                k["retired_at_utc"]=datetime.now(timezone.utc).isoformat()
        nk=_new_key(new_key_id,maxv+1)
        x["keys"].append(nk)
        x["active_key_id"]=new_key_id
        _write(path,x)
    return {"status":"PRIVATE_KEYRING_ROTATED","active_key_id":new_key_id,"key_version":maxv+1,"retired_keys_preserved":True,"key_material_printed":False}

def active_key(path:Path)->tuple[dict,bytes]:
    x=_load(path)
    kid=x["active_key_id"]
    return key_by_id_from_obj(x,kid)

def key_by_id(path:Path,key_id:str)->tuple[dict,bytes]:
    return key_by_id_from_obj(_load(path),key_id)

def key_by_id_from_obj(x:dict,key_id:str)->tuple[dict,bytes]:
    for k in x["keys"]:
        if k.get("key_id")==key_id:
            return k,base64.b64decode(k["material_b64"])
    raise RuntimeError("authorized backup key_id not found in private keyring")

def main():
    ap=argparse.ArgumentParser()
    sp=ap.add_subparsers(dest="cmd",required=True)
    a=sp.add_parser("init");a.add_argument("--keyring",type=Path,required=True);a.add_argument("--key-id",required=True)
    r=sp.add_parser("rotate");r.add_argument("--keyring",type=Path,required=True);r.add_argument("--new-key-id",required=True)
    s=sp.add_parser("status");s.add_argument("--keyring",type=Path,required=True)
    ns=ap.parse_args()
    if ns.cmd=="init":
        out=init_keyring(ns.keyring,ns.key_id)
    elif ns.cmd=="rotate":
        out=rotate_keyring(ns.keyring,ns.new_key_id)
    else:
        x=_load(ns.keyring);active=[k for k in x["keys"] if k["status"]=="ACTIVE"][0]
        out={"status":"PASS","active_key_id":active["key_id"],"key_version":active["key_version"],"retired_key_count":sum(k["status"]=="RETIRED" for k in x["keys"]),"key_material_printed":False}
    print(json.dumps(out,indent=2))
if __name__=="__main__":main()
