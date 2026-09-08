from __future__ import annotations
import argparse, json, re
from pathlib import Path
from typing import Any

ENTITLEMENT_MARKERS=("OSE_FREE_TRIAL","LICENSED_REALTIME_VENDOR","AUTHORIZED_READ_ONLY_BROKER_FEED","PRIVATE_INTERNAL_ONLY","PRIVATE_INTERNAL_STORE")
SECRET_KEY_RE=re.compile(r"(password|passwd|api[_-]?key|secret|access[_-]?token|refresh[_-]?token|authorization|credential|x[_-]?api[_-]?key)",re.I)

def json_hits(obj:Any,path:str="$")->list[str]:
    hits=[]
    if isinstance(obj,dict):
        for k,v in obj.items():
            p=f"{path}.{k}"
            if SECRET_KEY_RE.search(str(k)):hits.append("secret_key:"+p)
            if str(k)=="entitlement_mode" and str(v) in ENTITLEMENT_MARKERS:hits.append("entitlement:"+p)
            if str(v) in {"PRIVATE_INTERNAL_ONLY","PRIVATE_INTERNAL_STORE"}:hits.append("private_marker:"+p)
            hits.extend(json_hits(v,p))
    elif isinstance(obj,list):
        for i,v in enumerate(obj):hits.extend(json_hits(v,f"{path}[{i}]"))
    return hits

def scan(path:Path)->list[str]:
    if not path.exists() or not path.is_file():return []
    text=path.read_text(encoding="utf-8",errors="replace")
    hits=[]
    if path.suffix.lower()==".json":
        try:hits.extend(json_hits(json.loads(text)))
        except Exception:hits.append("invalid_json")
    for marker in ENTITLEMENT_MARKERS:
        if marker in text:hits.append("text_marker:"+marker)
    return sorted(set(hits))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--path",action="append",default=[]);ap.add_argument("--output",type=Path);a=ap.parse_args()
    unsafe={}
    present=[]
    for raw in a.path:
        p=Path(raw)
        if p.exists():present.append(str(p))
        hits=scan(p)
        if hits:unsafe[str(p)]=hits
    out={"version":"1.0","status":"PASS_PUBLIC_ARTIFACT_SAFETY" if not unsafe else "BLOCKED_UNSAFE_PUBLIC_ARTIFACT","present_paths":present,"unsafe":unsafe}
    s=json.dumps(out,ensure_ascii=False,indent=2)
    if a.output:a.output.write_text(s+"\n",encoding="utf-8")
    print(s)
    raise SystemExit(0 if not unsafe else 3)
if __name__=="__main__":main()
