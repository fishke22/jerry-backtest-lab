from __future__ import annotations
import copy, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("v",ROOT/"scripts"/"validate_jnu_entitled_exact_micro_evidence_v1.py"); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
c=json.loads((ROOT/"config"/"jnu_exact_micro_entitled_source_adapter_contract_v1.json").read_text()); r=json.loads((ROOT/"config"/"jnu_exact_micro_contract_roll_calendar_v1.json").read_text())
B={"entitlement_mode":"OSE_FREE_TRIAL","provider_name":"SYNTH","entitlement_reference":"opaque","transport_qualification_id":"q1","positive_margin_demonstrated":True,"canonical_symbol":"NK225MCU2026","exchange":"OSE","product":"Nikkei 225 micro Futures","contract_month":"2026-09","price":66050,"tick_size":5,"provider_timestamp":"2026-09-08T08:50:00+09:00","observed_at_taipei":"2026-09-08T07:50:30+08:00","exact_product":True,"continuous_contract":False,"broker_login_used":False,"trading_permission_used":False,"order_capable_session_used":False,"identity_evidence":{"exchange":"OSE","product":"Nikkei 225 micro Futures","contract_month":"2026-09","provider_symbol":"MC225U26"},"storage_scope":"PRIVATE_INTERNAL_ONLY","evidence_destination_class":"PRIVATE_INTERNAL_STORE","raw_public_distribution_permitted":False,"public_derived_permission_status":"UNCONFIRMED","third_party_cloud_processing_used":False,"third_party_cloud_permission_status":"NOT_APPLICABLE"}
T={}
def p(n,x):
    try:T[n]=m.validate(x,c,r)["status"]=="PASS"
    except Exception:T[n]=False
def f(n,x,s):
    try:m.validate(x,c,r);T[n]=False
    except RuntimeError as e:T[n]=s in str(e)
p("valid_free_trial",copy.deepcopy(B)); x=copy.deepcopy(B);x["entitlement_mode"]="LICENSED_REALTIME_VENDOR";p("valid_vendor",x)
x=copy.deepcopy(B);x["provider_timestamp"]="2026-09-08T08:34:59+09:00";f("stale",x,"quote stale")
x=copy.deepcopy(B);x["provider_timestamp"]="2026-09-08T08:50:31+09:00";f("future",x,"future")
x=copy.deepcopy(B);x["continuous_contract"]=True;f("continuous",x,"continuous_contract")
x=copy.deepcopy(B);x["broker_login_used"]=True;f("broker_auth",x,"broker_login_used")
x=copy.deepcopy(B);x["trading_permission_used"]=True;f("trading_permission",x,"trading_permission_used")
x=copy.deepcopy(B);x["api_key"]="x";f("secret_field",x,"secret-like")
x=copy.deepcopy(B);x["canonical_symbol"]="NK225MCQ2026";f("unknown_month",x,"roll calendar")
x=copy.deepcopy(B);x["price"]=66052;f("invalid_tick",x,"5-point tick")
x=copy.deepcopy(B);x["storage_scope"]="PUBLIC";f("public_storage_rejected",x,"PRIVATE_INTERNAL_ONLY")
x=copy.deepcopy(B);x["raw_public_distribution_permitted"]=True;f("raw_public_distribution_rejected",x,"raw_public_distribution_permitted")
x=copy.deepcopy(B);x["third_party_cloud_processing_used"]=True;x["third_party_cloud_permission_status"]="UNCONFIRMED";f("unapproved_cloud_rejected",x,"explicit approval")
status="PASS" if all(T.values()) else "FAIL"; print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T)},indent=2)); raise SystemExit(0 if status=="PASS" else 1)
