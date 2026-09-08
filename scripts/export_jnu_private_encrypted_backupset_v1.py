from __future__ import annotations
import argparse,json,os,shutil,uuid
from datetime import datetime,timezone
from pathlib import Path
from jnu_integrity_hash_v1 import canonical_text_sha256
from jnu_private_atomic_io_v1 import require_external
from jnu_private_backup_crypto_v1 import authenticate_manifest,encrypt_file,file_aad,sha256,wrap_aad,wrap_dek
from jnu_private_keyring_v1 import active_key
from jnu_private_lock_v1 import acquire_private_lock
from recover_jnu_private_entitled_ledger_v1 import scan
from validate_jnu_private_launch_manifest_v1 import load as load_manifest,validate as validate_manifest
ROOT=Path(__file__).resolve().parents[1];FRAMEWORK=ROOT/"config"/"jnu_operational_framework_current_v1_9.json";INCLUDE=["forecasts","outcomes","recovery/backups"]
def safe_rel(p:Path,root:Path)->str:
    rel=p.resolve().relative_to(root.resolve())
    if rel.is_absolute() or ".." in rel.parts:raise RuntimeError("unsafe backup relative path")
    return rel.as_posix()
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--manifest",type=Path,required=True);ap.add_argument("--keyring",type=Path,required=True);ap.add_argument("--destination-root",type=Path,required=True);ap.add_argument("--backupset-id");a=ap.parse_args()
    m=load_manifest(a.manifest);v=validate_manifest(m)
    if m["mode"]!="SYNTHETIC":raise RuntimeError("real entitled encrypted backup export remains prohibited pending provider terms and production key custody approval")
    root=Path(v["private_ledger_root"]).resolve();destroot=a.destination_root.resolve();require_external(a.keyring,"private keyring");require_external(destroot,"private encrypted backup destination")
    if root==destroot or root in destroot.parents or destroot in root.parents:raise RuntimeError("encrypted backup destination must be separate from ledger root")
    kmeta,kek=active_key(a.keyring);bid=a.backupset_id or ("JNU_PRIV_EBACKUP_"+uuid.uuid4().hex)
    if not bid.startswith("JNU_PRIV_EBACKUP_"):raise RuntimeError("invalid encrypted backupset id")
    out=destroot/bid
    if out.exists():raise RuntimeError("encrypted backupset destination already exists")
    framework=canonical_text_sha256(FRAMEWORK)
    with acquire_private_lock(root,"ledger-mutation",lease_seconds=300,wait_seconds=5) as lm:
        rs=scan(root,False,ignore_owner_token=lm["owner_token"])
        if rs["status"]!="PASS":raise RuntimeError("ledger recovery scan must PASS before encrypted backup export")
        files=[];latest=0.0
        for top in INCLUDE:
            base=root/Path(top)
            if not base.exists():continue
            for p in sorted(base.rglob("*")):
                if p.is_file():files.append((safe_rel(p,root),p));latest=max(latest,p.stat().st_mtime)
        dek=os.urandom(32);wn,wdek=wrap_dek(kek,dek,wrap_aad(bid,framework,kmeta["key_id"],kmeta["key_version"]))
        tmp=destroot/("."+bid+".tmp-"+uuid.uuid4().hex);payload=tmp/"payload";payload.mkdir(parents=True)
        try:
            entries=[]
            for idx,(rel,p) in enumerate(files):
                plain=p.read_bytes();aad=file_aad(bid,rel,framework,kmeta["key_id"],kmeta["key_version"],len(plain));nonce,cipher=encrypt_file(dek,plain,aad)
                cp=payload/f"{idx:06d}.bin";cp.write_bytes(cipher)
                try:os.chmod(cp,0o600)
                except OSError:pass
                entries.append({"path":rel,"ciphertext_path":f"payload/{cp.name}","nonce_b64":nonce,"ciphertext_sha256":sha256(cipher),"ciphertext_size":len(cipher),"plaintext_size":len(plain)})
            core={"version":"1.1","artifact_class":"JNU_PRIVATE_ENCRYPTED_BACKUP_SET","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"backupset_id":bid,"created_at_utc":datetime.now(timezone.utc).isoformat(),"source_latest_record_mtime_utc":datetime.fromtimestamp(latest or datetime.now(timezone.utc).timestamp(),timezone.utc).isoformat(),"source_mode":"SYNTHETIC","source_launch_id":m["launch_id"],"framework_sha256":framework,"algorithm":"AES-256-GCM","envelope":True,"key_id":kmeta["key_id"],"key_version":kmeta["key_version"],"wrapped_dek_nonce_b64":wn,"wrapped_dek_b64":wdek,"key_material_present":False,"plaintext_hash_present":False,"file_count":len(entries),"files":entries}
            mn,mt=authenticate_manifest(dek,core);bm=dict(core);bm["manifest_auth_nonce_b64"]=mn;bm["manifest_auth_tag_b64"]=mt
            (tmp/"manifest.json").write_text(json.dumps(bm,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            try:os.chmod(tmp/"manifest.json",0o600);os.chmod(tmp,0o700);os.chmod(payload,0o700)
            except OSError:pass
            os.replace(tmp,out)
        finally:
            if tmp.exists():shutil.rmtree(tmp)
    print(json.dumps({"status":"PRIVATE_ENCRYPTED_BACKUP_SET_EXPORTED","backupset_id":bid,"key_id":kmeta["key_id"],"key_version":kmeta["key_version"],"file_count":len(files),"envelope":True,"key_material_printed":False,"raw_private_data_printed":False,"public_output_created":False},indent=2))
if __name__=="__main__":main()
