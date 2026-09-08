from __future__ import annotations
import argparse,json,os,re,secrets
from datetime import datetime,timezone
from pathlib import Path
from jnu_private_atomic_io_v1 import _atomic_bytes,require_external,write_replace_json
from jnu_private_lock_v1 import acquire_private_lock

KEY_ID_RE=re.compile(r"^JNU_KEY_[A-Za-z0-9._-]{6,120}$")
VALID_STATUS={"ACTIVE_ENCRYPT_DECRYPT","RETIRED_DECRYPT_ONLY"}

def _material_dir(path:Path)->Path:
    return path.resolve().parent/(path.name+".keys")
def _key_path(path:Path,key_id:str,version:int)->Path:
    return _material_dir(path)/f"{key_id}.v{int(version)}.key"
def _check_mode(path:Path)->None:
    if os.name!="nt":
        mode=path.stat().st_mode & 0o777
        if mode & 0o077:raise RuntimeError("private key file permissions must be 0600 or stricter")
def _load(path:Path)->dict:
    require_external(path,"private keyring metadata")
    x=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x,dict) or x.get("artifact_class")!="JNU_PRIVATE_KEYRING":raise RuntimeError("private keyring artifact invalid")
    if "material_b64" in path.read_text(encoding="utf-8"):raise RuntimeError("keyring metadata must not contain key material")
    _check_mode(path)
    keys=x.get("keys")
    if not isinstance(keys,list) or not keys:raise RuntimeError("private keyring keys missing")
    active=[k for k in keys if k.get("status")=="ACTIVE_ENCRYPT_DECRYPT"]
    if len(active)!=1:raise RuntimeError("private keyring must contain exactly one active key")
    for k in keys:
        if k.get("status") not in VALID_STATUS:raise RuntimeError("private key status invalid")
        p=_key_path(path,k["key_id"],k["key_version"])
        if not p.exists() or len(p.read_bytes())!=32:raise RuntimeError("private KEK material missing or invalid")
        _check_mode(p)
    return x
def _write_meta(path:Path,obj:dict)->None:
    require_external(path,"private keyring metadata")
    path.parent.mkdir(parents=True,exist_ok=True)
    write_replace_json(path,obj);_check_mode(path)
def _write_key(path:Path,key_id:str,version:int,material:bytes)->None:
    if len(material)!=32:raise RuntimeError("private KEK must be 32 bytes")
    p=_key_path(path,key_id,version);p.parent.mkdir(parents=True,exist_ok=True)
    _atomic_bytes(p,material,mode=0o600,replace=False);_check_mode(p)
def init_keyring(path:Path,key_id:str)->dict:
    require_external(path,"private keyring metadata")
    if path.exists():raise RuntimeError("private keyring already exists")
    if not KEY_ID_RE.fullmatch(key_id):raise RuntimeError("invalid key_id")
    now=datetime.now(timezone.utc).isoformat();_write_key(path,key_id,1,secrets.token_bytes(32))
    obj={"version":"1.1","artifact_class":"JNU_PRIVATE_KEYRING","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"metadata_contains_key_material":False,"active_key_id":key_id,"active_key_version":1,"keys":[{"key_id":key_id,"key_version":1,"algorithm":"AES-256-GCM","status":"ACTIVE_ENCRYPT_DECRYPT","created_at_utc":now}]}
    _write_meta(path,obj)
    return {"status":"PRIVATE_KEYRING_INITIALIZED","active_key_id":key_id,"key_version":1,"key_material_printed":False}
def rotate_keyring(path:Path,new_key_id:str)->dict:
    root=path.resolve().parent;require_external(root,"private keyring directory")
    if not KEY_ID_RE.fullmatch(new_key_id):raise RuntimeError("invalid new key_id")
    with acquire_private_lock(root,"keyring:"+path.name,lease_seconds=120,wait_seconds=5):
        x=_load(path)
        if any(k["key_id"]==new_key_id for k in x["keys"]):raise RuntimeError("new key_id already exists")
        maxv=max(int(k["key_version"]) for k in x["keys"]);ver=maxv+1;now=datetime.now(timezone.utc).isoformat()
        for k in x["keys"]:
            if k["status"]=="ACTIVE_ENCRYPT_DECRYPT":k["status"]="RETIRED_DECRYPT_ONLY";k["retired_at_utc"]=now
        _write_key(path,new_key_id,ver,secrets.token_bytes(32))
        x["keys"].append({"key_id":new_key_id,"key_version":ver,"algorithm":"AES-256-GCM","status":"ACTIVE_ENCRYPT_DECRYPT","created_at_utc":now});x["active_key_id"]=new_key_id;x["active_key_version"]=ver;x["updated_at_utc"]=now;_write_meta(path,x)
    return {"status":"PRIVATE_KEYRING_ROTATED","active_key_id":new_key_id,"key_version":ver,"previous_version":maxv,"retired_keys_preserved":True,"key_material_printed":False}
def key_by_id_version(path:Path,key_id:str,key_version:int,for_encrypt:bool=False)->tuple[dict,bytes]:
    x=_load(path);hits=[k for k in x["keys"] if k["key_id"]==key_id and int(k["key_version"])==int(key_version)]
    if len(hits)!=1:raise RuntimeError("authorized backup key id/version not found")
    k=hits[0]
    if for_encrypt and k["status"]!="ACTIVE_ENCRYPT_DECRYPT":raise RuntimeError("selected key version is not active for encryption")
    return k,_key_path(path,key_id,key_version).read_bytes()
def active_key(path:Path)->tuple[dict,bytes]:
    x=_load(path);return key_by_id_version(path,x["active_key_id"],x["active_key_version"],for_encrypt=True)
def key_by_id(path:Path,key_id:str)->tuple[dict,bytes]:
    x=_load(path);hits=[k for k in x["keys"] if k["key_id"]==key_id]
    if len(hits)!=1:raise RuntimeError("key_id is missing or ambiguous; use key id/version")
    return key_by_id_version(path,key_id,hits[0]["key_version"])
def main():
    ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest="cmd",required=True)
    a=sp.add_parser("init");a.add_argument("--keyring",type=Path,required=True);a.add_argument("--key-id",required=True)
    r=sp.add_parser("rotate");r.add_argument("--keyring",type=Path,required=True);r.add_argument("--new-key-id",required=True)
    s=sp.add_parser("status");s.add_argument("--keyring",type=Path,required=True)
    ns=ap.parse_args()
    if ns.cmd=="init":out=init_keyring(ns.keyring,ns.key_id)
    elif ns.cmd=="rotate":out=rotate_keyring(ns.keyring,ns.new_key_id)
    else:
        x=_load(ns.keyring);out={"status":"PASS","active_key_id":x["active_key_id"],"active_key_version":x["active_key_version"],"versions":[{"key_id":k["key_id"],"key_version":k["key_version"],"status":k["status"]} for k in x["keys"]],"metadata_contains_key_material":False,"key_material_printed":False}
    print(json.dumps(out,indent=2))
if __name__=="__main__":main()
