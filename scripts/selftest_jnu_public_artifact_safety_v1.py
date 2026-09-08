from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PY=sys.executable;S=ROOT/"scripts"/"check_jnu_public_artifact_safety_v1.py";T={}
with tempfile.TemporaryDirectory(prefix="jnu_artifact_guard_") as td0:
    td=Path(td0)
    safe=td/"safe.json";safe.write_text(json.dumps({"source_id":"JPX_OSE_OFFICIAL","price":65000})+"\n")
    cp=subprocess.run([PY,str(S),"--path",str(safe)],cwd=ROOT,capture_output=True,text=True);T["safe_public_quote_pass"]=cp.returncode==0
    ent=td/"ent.json";ent.write_text(json.dumps({"entitlement_mode":"OSE_FREE_TRIAL","price":65000})+"\n")
    cp=subprocess.run([PY,str(S),"--path",str(ent)],cwd=ROOT,capture_output=True,text=True);T["entitled_json_rejected"]=cp.returncode!=0
    priv=td/"priv.log";priv.write_text("storage=PRIVATE_INTERNAL_ONLY\n")
    cp=subprocess.run([PY,str(S),"--path",str(priv)],cwd=ROOT,capture_output=True,text=True);T["private_marker_log_rejected"]=cp.returncode!=0
    missing=td/"missing.json"
    cp=subprocess.run([PY,str(S),"--path",str(missing)],cwd=ROOT,capture_output=True,text=True);T["missing_path_safe"]=cp.returncode==0
status="PASS" if all(T.values()) else "FAIL";print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T)},indent=2));raise SystemExit(0 if status=="PASS" else 1)
