from __future__ import annotations
import base64,hashlib,json,os
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def b64(x:bytes)->str:return base64.b64encode(x).decode("ascii")
def unb64(x:str)->bytes:return base64.b64decode(x.encode("ascii"),validate=True)
def canon(x)->bytes:return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
def sha256(x:bytes)->str:return hashlib.sha256(x).hexdigest()
def wrap_aad(bid,framework,key_id,key_version):
    return canon({"purpose":"JNU_PRIVATE_BACKUP_DEK_WRAP_V1","backupset_id":bid,"framework_sha256":framework,"key_id":key_id,"key_version":int(key_version)})
def file_aad(bid,rel,framework,key_id,key_version,plaintext_size):
    return canon({"purpose":"JNU_PRIVATE_BACKUP_FILE_V1","backupset_id":bid,"path":rel,"framework_sha256":framework,"key_id":key_id,"key_version":int(key_version),"plaintext_size":int(plaintext_size)})
def wrap_dek(kek:bytes,dek:bytes,aad:bytes)->tuple[str,str]:
    nonce=os.urandom(12);return b64(nonce),b64(AESGCM(kek).encrypt(nonce,dek,aad))
def unwrap_dek(kek:bytes,nonce_b64:str,wrapped_b64:str,aad:bytes)->bytes:
    try:return AESGCM(kek).decrypt(unb64(nonce_b64),unb64(wrapped_b64),aad)
    except InvalidTag as e:raise RuntimeError("PRIVATE_BACKUP_WRAPPED_KEY_AUTH_FAILED") from e
def encrypt_file(dek:bytes,data:bytes,aad:bytes)->tuple[str,bytes]:
    nonce=os.urandom(12);return b64(nonce),AESGCM(dek).encrypt(nonce,data,aad)
def decrypt_file(dek:bytes,nonce_b64:str,cipher:bytes,aad:bytes)->bytes:
    try:return AESGCM(dek).decrypt(unb64(nonce_b64),cipher,aad)
    except InvalidTag as e:raise RuntimeError("PRIVATE_BACKUP_CIPHERTEXT_AUTH_FAILED") from e
def authenticate_manifest(dek:bytes,core:dict)->tuple[str,str]:
    nonce=os.urandom(12);tag=AESGCM(dek).encrypt(nonce,b"",canon(core));return b64(nonce),b64(tag)
def verify_manifest(dek:bytes,core:dict,nonce_b64:str,tag_b64:str)->None:
    try:
        if AESGCM(dek).decrypt(unb64(nonce_b64),unb64(tag_b64),canon(core))!=b"":raise RuntimeError("manifest authentication plaintext unexpected")
    except InvalidTag as e:raise RuntimeError("PRIVATE_BACKUP_MANIFEST_AUTH_FAILED") from e
