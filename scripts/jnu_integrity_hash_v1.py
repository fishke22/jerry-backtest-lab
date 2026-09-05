from __future__ import annotations
import hashlib
from pathlib import Path

METHOD_ID="SHA256_TEXT_EOL_CRLF_V1"
RAW_METHOD_ID="SHA256_RAW_BYTES_V1"

def canonical_text_bytes(path:Path)->bytes:
    raw=Path(path).read_bytes()
    lf=raw.replace(b"\r\n",b"\n").replace(b"\r",b"\n")
    return lf.replace(b"\n",b"\r\n")

def canonical_text_sha256(path:Path)->str:
    return hashlib.sha256(canonical_text_bytes(path)).hexdigest()

def raw_sha256(path:Path)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
