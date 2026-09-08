from __future__ import annotations
import argparse,base64,hashlib,json,subprocess,sys
from pathlib import Path,PurePosixPath
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from export_jnu_private_encrypted_backupset_v1 import aad_bytes
from jnu_integrity_hash_v1 import canonical_text_sha256
from jnu_private_atomic_io_v1 import _atomic_bytes,require_external
from jnu_private_keyring_v1 import key_by_id
from recover_jnu_private_entitled_ledger_v1 import scan
from validate_jnu_private_restore_authorization_v1 import load as load_auth,validate as validate_auth

ROOT=Path(__file__).resolve().parents[1]
FRAMEWORK=ROOT/"config"/"jnu_operational_framework_current_v1_9.json"
SCORER=ROOT/"scripts"/"score_jnu_private_entitled_live_shadow_v1.py"

def safe_rel(s:str)->Path:
    p=PurePosixPath(s)
    if p.is_absolute() or ".." in p.parts or "." in p.parts:
        raise RuntimeError("encrypted backup manifest path traversal rejected")
    return Path(*p.parts)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--backupset",type=Path,required=True)
    ap.add_argument("--keyring",type=Path,required=True)
    ap.add_argument("--authorization",type=Path,required=True)
    a=ap.parse_args()

    bs=a.backupset.resolve();require_external(bs,"private encrypted backupset");require_external(a.keyring,"private keyring")
    bm=json.loads((bs/"manifest.json").read_text(encoding="utf-8"))
    if bm.get("artifact_class")!="JNU_PRIVATE_ENCRYPTED_BACKUP_SET" or bm.get("storage_scope")!="PRIVATE_INTERNAL_ONLY":
        raise RuntimeError("encrypted backupset manifest invalid")
    if bm.get("algorithm")!="AES-256-GCM" or bm.get("key_material_present") is not False:
        raise RuntimeError("encrypted backup cryptography manifest invalid")
    if bm.get("framework_sha256")!=canonical_text_sha256(FRAMEWORK):
        raise RuntimeError("encrypted backup framework SHA mismatch")

    av=validate_auth(load_auth(a.authorization))
    if av["backupset_id"]!=bm["backupset_id"] or av["authorized_key_id"]!=bm["key_id"]:
        raise RuntimeError("restore authorization does not match backupset/key")
    dest=Path(av["destination_ledger_root"]).resolve()
    if dest.exists() and any(dest.iterdir()):
        raise RuntimeError("encrypted DR import destination must be empty")
    kmeta,key=key_by_id(a.keyring,bm["key_id"])
    if int(kmeta["key_version"])!=int(bm["key_version"]):
        raise RuntimeError("private key version mismatch")

    aes=AESGCM(key)
    decoded=[]
    for e in bm.get("files",[]):
        rel=safe_rel(str(e["path"]))
        cpath=bs/safe_rel(str(e["ciphertext_path"]))
        if not cpath.is_file():
            raise RuntimeError("encrypted payload file missing: "+str(rel))
        cipher=cpath.read_bytes()
        if len(cipher)!=int(e["ciphertext_size"]) or hashlib.sha256(cipher).hexdigest()!=e["ciphertext_sha256"]:
            raise RuntimeError("encrypted payload ciphertext integrity mismatch: "+str(rel))
        nonce=base64.b64decode(e["nonce_b64"],validate=True)
        if len(nonce)!=12:
            raise RuntimeError("encrypted payload nonce invalid")
        aad=aad_bytes(bm["backupset_id"],str(e["path"]),bm["framework_sha256"],bm["key_id"],bm["key_version"])
        try:
            plain=aes.decrypt(nonce,cipher,aad)
        except InvalidTag as ex:
            raise RuntimeError("encrypted payload authentication failed") from ex
        if len(plain)!=int(e["plaintext_size"]) or hashlib.sha256(plain).hexdigest()!=e["plaintext_sha256"]:
            raise RuntimeError("encrypted payload plaintext integrity mismatch: "+str(rel))
        decoded.append((rel,plain))
    if len(decoded)!=int(bm.get("file_count",-1)):
        raise RuntimeError("encrypted backup file count mismatch")

    dest.mkdir(parents=True,exist_ok=True)
    for rel,plain in decoded:
        _atomic_bytes(dest/rel,plain,mode=0o600,replace=False)
    rs=scan(dest,False)
    if rs["status"]!="PASS":
        raise RuntimeError("encrypted restored ledger recovery scan failed")
    out=dest/"results"/"dr_revalidated_v1.json"
    cp=subprocess.run([sys.executable,str(SCORER),"--private-ledger-root",str(dest),"--output",str(out)],cwd=ROOT,capture_output=True,text=True)
    if cp.returncode!=0:
        raise RuntimeError("encrypted restored ledger scorer revalidation failed: "+(cp.stderr or cp.stdout).strip())
    print(json.dumps({"status":"PRIVATE_ENCRYPTED_BACKUP_IMPORTED_AND_REVALIDATED","backupset_id":bm["backupset_id"],"key_id":bm["key_id"],"file_count":len(decoded),"recovery_scan":"PASS","scorer_revalidation":"PASS","key_material_printed":False,"raw_private_data_printed":False,"public_output_created":False},indent=2))
if __name__=="__main__":main()
