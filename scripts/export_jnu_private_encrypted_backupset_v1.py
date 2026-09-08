from __future__ import annotations
import argparse,base64,hashlib,json,os,shutil,uuid
from datetime import datetime,timezone
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jnu_integrity_hash_v1 import canonical_text_sha256
from jnu_private_atomic_io_v1 import require_external
from jnu_private_keyring_v1 import active_key
from jnu_private_lock_v1 import acquire_private_lock
from recover_jnu_private_entitled_ledger_v1 import scan
from validate_jnu_private_launch_manifest_v1 import load as load_manifest,validate as validate_manifest

ROOT=Path(__file__).resolve().parents[1]
FRAMEWORK=ROOT/"config"/"jnu_operational_framework_current_v1_9.json"
INCLUDE=["forecasts","outcomes","recovery/backups"]

def safe_rel(p:Path,root:Path)->str:
    rel=p.resolve().relative_to(root.resolve())
    if rel.is_absolute() or ".." in rel.parts:
        raise RuntimeError("unsafe backup relative path")
    return rel.as_posix()

def aad_bytes(bid:str,rel:str,framework_sha:str,key_id:str,key_version:int)->bytes:
    return json.dumps({"backupset_id":bid,"path":rel,"framework_sha256":framework_sha,"key_id":key_id,"key_version":int(key_version)},sort_keys=True,separators=(",",":")).encode("utf-8")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--keyring",type=Path,required=True)
    ap.add_argument("--destination-root",type=Path,required=True)
    ap.add_argument("--backupset-id")
    a=ap.parse_args()

    m=load_manifest(a.manifest);v=validate_manifest(m)
    if m["mode"]!="SYNTHETIC":
        raise RuntimeError("real entitled encrypted backup export remains prohibited pending provider terms and production key custody approval")
    root=Path(v["private_ledger_root"]).resolve()
    destroot=a.destination_root.resolve()
    require_external(a.keyring,"private keyring")
    require_external(destroot,"private encrypted backup destination")
    if root==destroot or root in destroot.parents or destroot in root.parents:
        raise RuntimeError("encrypted backup destination must be separate from ledger root")
    kmeta,key=active_key(a.keyring)
    bid=a.backupset_id or ("JNU_PRIV_EBACKUP_"+uuid.uuid4().hex)
    if not bid.startswith("JNU_PRIV_EBACKUP_"):
        raise RuntimeError("invalid encrypted backupset id")
    out=destroot/bid
    if out.exists():
        raise RuntimeError("encrypted backupset destination already exists")
    framework_sha=canonical_text_sha256(FRAMEWORK)

    with acquire_private_lock(root,"ledger-mutation",lease_seconds=300,wait_seconds=5) as lm:
        rs=scan(root,False,ignore_owner_token=lm["owner_token"])
        if rs["status"]!="PASS":
            raise RuntimeError("ledger recovery scan must PASS before encrypted backup export")
        files=[]
        latest_mtime=0.0
        for top in INCLUDE:
            base=root/Path(top)
            if not base.exists():continue
            for p in sorted(base.rglob("*")):
                if p.is_file():
                    rel=safe_rel(p,root)
                    files.append((rel,p))
                    latest_mtime=max(latest_mtime,p.stat().st_mtime)
        tmp=destroot/("."+bid+".tmp-"+uuid.uuid4().hex)
        payload=tmp/"payload"
        payload.mkdir(parents=True)
        try:
            entries=[]
            aes=AESGCM(key)
            for idx,(rel,p) in enumerate(files):
                plain=p.read_bytes()
                nonce=os.urandom(12)
                aad=aad_bytes(bid,rel,framework_sha,kmeta["key_id"],kmeta["key_version"])
                cipher=aes.encrypt(nonce,plain,aad)
                cp=payload/f"{idx:06d}.bin"
                cp.write_bytes(cipher)
                try:os.chmod(cp,0o600)
                except OSError:pass
                entries.append({
                  "path":rel,
                  "ciphertext_path":f"payload/{cp.name}",
                  "nonce_b64":base64.b64encode(nonce).decode("ascii"),
                  "ciphertext_sha256":hashlib.sha256(cipher).hexdigest(),
                  "ciphertext_size":len(cipher),
                  "plaintext_sha256":hashlib.sha256(plain).hexdigest(),
                  "plaintext_size":len(plain)
                })
            bm={
              "version":"1.0","artifact_class":"JNU_PRIVATE_ENCRYPTED_BACKUP_SET",
              "storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,
              "backupset_id":bid,"created_at_utc":datetime.now(timezone.utc).isoformat(),
              "source_latest_record_mtime_utc":datetime.fromtimestamp(latest_mtime or datetime.now(timezone.utc).timestamp(),timezone.utc).isoformat(),
              "source_launch_id":m["launch_id"],"framework_sha256":framework_sha,
              "algorithm":"AES-256-GCM","key_id":kmeta["key_id"],"key_version":kmeta["key_version"],
              "key_material_present":False,"file_count":len(entries),"files":entries
            }
            (tmp/"manifest.json").write_text(json.dumps(bm,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            try:os.chmod(tmp/"manifest.json",0o600);os.chmod(tmp,0o700);os.chmod(payload,0o700)
            except OSError:pass
            os.replace(tmp,out)
        finally:
            if tmp.exists():shutil.rmtree(tmp)
    print(json.dumps({"status":"PRIVATE_ENCRYPTED_BACKUP_SET_EXPORTED","backupset_id":bid,"key_id":kmeta["key_id"],"key_version":kmeta["key_version"],"file_count":len(files),"key_material_printed":False,"raw_private_data_printed":False,"public_output_created":False},indent=2))
if __name__=="__main__":main()
