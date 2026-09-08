from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path,PurePosixPath
from jnu_integrity_hash_v1 import canonical_text_sha256
from jnu_private_atomic_io_v1 import _atomic_bytes,require_external,write_replace_json
from jnu_private_backup_crypto_v1 import decrypt_file,file_aad,sha256,unwrap_dek,verify_manifest,wrap_aad
from jnu_private_keyring_v1 import key_by_id_version
from recover_jnu_private_entitled_ledger_v1 import scan
from validate_jnu_private_restore_authorization_v1 import load as load_auth,validate as validate_auth
ROOT=Path(__file__).resolve().parents[1];FRAMEWORK=ROOT/"config"/"jnu_operational_framework_current_v1_9.json";SCORER=ROOT/"scripts"/"score_jnu_private_entitled_live_shadow_v1.py"
def safe_rel(s:str)->Path:
    p=PurePosixPath(s)
    if p.is_absolute() or ".." in p.parts or "." in p.parts:raise RuntimeError("encrypted backup manifest path traversal rejected")
    return Path(*p.parts)
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--backupset",type=Path,required=True);ap.add_argument("--keyring",type=Path,required=True);ap.add_argument("--authorization",type=Path,required=True);ap.add_argument("--now-utc");a=ap.parse_args()
    bs=a.backupset.resolve();require_external(bs,"private encrypted backupset");require_external(a.keyring,"private keyring")
    bm=json.loads((bs/"manifest.json").read_text(encoding="utf-8"))
    if bm.get("artifact_class")!="JNU_PRIVATE_ENCRYPTED_BACKUP_SET" or bm.get("storage_scope")!="PRIVATE_INTERNAL_ONLY":raise RuntimeError("encrypted backupset manifest invalid")
    if bm.get("algorithm")!="AES-256-GCM" or bm.get("envelope") is not True or bm.get("key_material_present") is not False or bm.get("plaintext_hash_present") is not False:raise RuntimeError("encrypted backup cryptography manifest invalid")
    if bm.get("framework_sha256")!=canonical_text_sha256(FRAMEWORK):raise RuntimeError("encrypted backup framework SHA mismatch")
    av=validate_auth(load_auth(a.authorization),bm,a.now_utc);dest=Path(av["destination_ledger_root"]).resolve()
    if dest.exists() and any(dest.iterdir()):raise RuntimeError("encrypted DR import destination must be empty")
    kmeta,kek=key_by_id_version(a.keyring,bm["key_id"],bm["key_version"],for_encrypt=False)
    dek=unwrap_dek(kek,bm["wrapped_dek_nonce_b64"],bm["wrapped_dek_b64"],wrap_aad(bm["backupset_id"],bm["framework_sha256"],bm["key_id"],bm["key_version"]))
    core=dict(bm);mn=core.pop("manifest_auth_nonce_b64");mt=core.pop("manifest_auth_tag_b64");verify_manifest(dek,core,mn,mt)
    decoded=[]
    for e in bm.get("files",[]):
        rel=safe_rel(str(e["path"]));cpath=bs/safe_rel(str(e["ciphertext_path"]))
        if not cpath.is_file():raise RuntimeError("encrypted payload file missing: "+str(rel))
        cipher=cpath.read_bytes()
        if len(cipher)!=int(e["ciphertext_size"]) or sha256(cipher)!=e["ciphertext_sha256"]:raise RuntimeError("encrypted payload ciphertext integrity mismatch: "+str(rel))
        aad=file_aad(bm["backupset_id"],str(e["path"]),bm["framework_sha256"],bm["key_id"],bm["key_version"],int(e["plaintext_size"]));plain=decrypt_file(dek,e["nonce_b64"],cipher,aad)
        if len(plain)!=int(e["plaintext_size"]):raise RuntimeError("encrypted payload plaintext size mismatch: "+str(rel))
        decoded.append((rel,plain))
    if len(decoded)!=int(bm.get("file_count",-1)):raise RuntimeError("encrypted backup file count mismatch")
    dest.mkdir(parents=True,exist_ok=True)
    for rel,plain in decoded:_atomic_bytes(dest/rel,plain,mode=0o600,replace=False)
    rs=scan(dest,False)
    if rs["status"]!="PASS":raise RuntimeError("encrypted restored ledger recovery scan failed")
    out=dest/"results"/"dr_revalidated_v1.json";cp=subprocess.run([sys.executable,str(SCORER),"--private-ledger-root",str(dest),"--output",str(out)],cwd=ROOT,capture_output=True,text=True)
    if cp.returncode!=0:raise RuntimeError("encrypted restored ledger scorer revalidation failed: "+(cp.stderr or cp.stdout).strip())
    receipt={"version":"1.0","artifact_class":"JNU_PRIVATE_RESTORE_AUTHORIZATION_RECEIPT","storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"restore_id":av["restore_id"],"backupset_id":bm["backupset_id"],"key_id":bm["key_id"],"key_version":bm["key_version"],"restore_status":"PASS","recovery_scan":"PASS","scorer_revalidation":"PASS"}
    write_replace_json(dest/"recovery"/"restore_authorization_receipt.json",receipt)
    print(json.dumps({"status":"PRIVATE_ENCRYPTED_BACKUP_IMPORTED_AND_REVALIDATED","backupset_id":bm["backupset_id"],"key_id":bm["key_id"],"key_version":bm["key_version"],"file_count":len(decoded),"restore_id":av["restore_id"],"recovery_scan":"PASS","scorer_revalidation":"PASS","key_material_printed":False,"raw_private_data_printed":False,"public_output_created":False},indent=2))
if __name__=="__main__":main()
