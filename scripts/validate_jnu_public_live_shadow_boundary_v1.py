from __future__ import annotations
import argparse, json, re
from pathlib import Path
from typing import Any

ENTITLEMENT_MODES={"OSE_FREE_TRIAL","LICENSED_REALTIME_VENDOR","AUTHORIZED_READ_ONLY_BROKER_FEED"}
SECRET_KEY_RE=re.compile(r"(password|passwd|api[_-]?key|secret|access[_-]?token|refresh[_-]?token|authorization|credential|x[_-]?api[_-]?key)",re.I)

def walk(obj:Any,path:str="$"):
    if isinstance(obj,dict):
        for k,v in obj.items():
            yield f"{path}.{k}",k,v
            yield from walk(v,f"{path}.{k}")
    elif isinstance(obj,list):
        for i,v in enumerate(obj):
            yield from walk(v,f"{path}[{i}]")

def validate_public_live_shadow_boundary(x:dict)->dict:
    if not isinstance(x,dict):
        raise RuntimeError("forecast envelope must be an object")
    entitlement_hits=[]
    secret_hits=[]
    private_raw_hits=[]
    for path,k,v in walk(x):
        if SECRET_KEY_RE.search(str(k)):
            secret_hits.append(path)
        if str(k)=="entitlement_mode" and str(v) in ENTITLEMENT_MODES:
            entitlement_hits.append(path)
        if str(k) in {"storage_scope","raw_evidence_storage_scope"} and str(v)=="PRIVATE_INTERNAL_ONLY":
            private_raw_hits.append(path)
        if str(k)=="evidence_destination_class" and str(v)=="PRIVATE_INTERNAL_STORE":
            private_raw_hits.append(path)
    if secret_hits:
        raise RuntimeError("PUBLIC_LEDGER_SECRET_LIKE_FIELD_PROHIBITED: "+",".join(secret_hits))
    if entitlement_hits or private_raw_hits:
        detail=",".join(entitlement_hits+private_raw_hits)
        raise RuntimeError("ENTITLED_SOURCE_PUBLIC_LEDGER_PROHIBITED: "+detail)
    return {
      "version":"1.0",
      "status":"PASS_PUBLIC_LIVE_SHADOW_BOUNDARY",
      "entitled_source_present":False,
      "private_raw_evidence_marker_present":False,
      "secret_like_field_present":False,
      "public_raw_entitled_market_data_written":False
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",type=Path,required=True);ap.add_argument("--output",type=Path);a=ap.parse_args()
    x=json.loads(a.input.read_text(encoding="utf-8"))
    out=validate_public_live_shadow_boundary(x);s=json.dumps(out,ensure_ascii=False,indent=2)
    if a.output:a.output.write_text(s+"\n",encoding="utf-8")
    print(s)
if __name__=="__main__":main()
