from __future__ import annotations
import copy, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("m",ROOT/"scripts"/"validate_jnu_public_live_shadow_boundary_v1.py");m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
B={"reference_source":"JPX official public","reference_source_metadata":{"source_id":"JPX_OSE_OFFICIAL","exact_product":True,"continuous_contract":False}}
T={}
def p(n,x):
    try:T[n]=m.validate_public_live_shadow_boundary(x)["status"]=="PASS_PUBLIC_LIVE_SHADOW_BOUNDARY"
    except Exception:T[n]=False
def f(n,x,s):
    try:m.validate_public_live_shadow_boundary(x);T[n]=False
    except RuntimeError as e:T[n]=s in str(e)
p("public_jpx_pass",copy.deepcopy(B))
x=copy.deepcopy(B);x["reference_source_metadata"]["source_id"]="OSE";p("public_tradingview_pass",x)
for mode in ["OSE_FREE_TRIAL","LICENSED_REALTIME_VENDOR","AUTHORIZED_READ_ONLY_BROKER_FEED"]:
    x=copy.deepcopy(B);x["reference_source_metadata"]["entitlement_mode"]=mode;f("reject_"+mode.lower(),x,"ENTITLED_SOURCE_PUBLIC_LEDGER_PROHIBITED")
x=copy.deepcopy(B);x["reference_source_metadata"]["storage_scope"]="PRIVATE_INTERNAL_ONLY";f("private_storage_marker_rejected",x,"ENTITLED_SOURCE_PUBLIC_LEDGER_PROHIBITED")
x=copy.deepcopy(B);x["api_key"]="never";f("secret_key_rejected",x,"PUBLIC_LEDGER_SECRET_LIKE_FIELD_PROHIBITED")
x=copy.deepcopy(B);x["nested"]={"authorization":"never"};f("nested_secret_rejected",x,"PUBLIC_LEDGER_SECRET_LIKE_FIELD_PROHIBITED")
status="PASS" if all(T.values()) else "FAIL";print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T)},indent=2));raise SystemExit(0 if status=="PASS" else 1)
