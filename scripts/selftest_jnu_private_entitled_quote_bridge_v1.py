from __future__ import annotations
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];PY=sys.executable
SCRIPT=ROOT/"scripts"/"build_jnu_private_entitled_quote_bundle_v1.py"
FD=ROOT/"live_shadow"/"forecasts";OD=ROOT/"live_shadow"/"outcomes"

def counts():
    return (len(list(FD.glob("*.json"))) if FD.exists() else 0,len(list(OD.glob("*.json"))) if OD.exists() else 0)

E={"entitlement_mode":"OSE_FREE_TRIAL","provider_name":"SYNTH","entitlement_reference":"opaque","transport_qualification_id":"q1","positive_margin_demonstrated":True,"canonical_symbol":"NK225MCU2026","exchange":"OSE","product":"Nikkei 225 micro Futures","contract_month":"2026-09","price":66050,"tick_size":5,"provider_timestamp":"2026-09-08T08:50:00+09:00","observed_at_taipei":"2026-09-08T07:50:30+08:00","exact_product":True,"continuous_contract":False,"broker_login_used":False,"trading_permission_used":False,"order_capable_session_used":False,"identity_evidence":{"exchange":"OSE","product":"Nikkei 225 micro Futures","contract_month":"2026-09","provider_symbol":"MC225U26"},"storage_scope":"PRIVATE_INTERNAL_ONLY","evidence_destination_class":"PRIVATE_INTERNAL_STORE","raw_public_distribution_permitted":False,"public_derived_permission_status":"UNCONFIRMED","third_party_cloud_processing_used":False,"third_party_cloud_permission_status":"NOT_APPLICABLE"}
M={"entitlement_mode":"OSE_FREE_TRIAL","raw_evidence_storage_scope":"PRIVATE_INTERNAL_ONLY","evidence_destination_class":"PRIVATE_INTERNAL_STORE","target_repository_visibility":"PRIVATE","raw_market_data_in_public_artifact":False,"third_party_cloud_processing_used":False,"third_party_cloud_permission_status":"NOT_APPLICABLE","public_output_requested":False,"public_output_type":"NONE","public_publication_permission_status":"UNCONFIRMED","reconstructive_market_data_fields_in_public_output":False}

before=counts();T={}
with tempfile.TemporaryDirectory(prefix="jnu_private_bridge_ext_") as td0:
    td=Path(td0);e=td/"evidence.json";m=td/"manifest.json";store=td/"store"
    e.write_text(json.dumps(E)+"\n");m.write_text(json.dumps(M)+"\n")
    cp=subprocess.run([PY,str(SCRIPT),"--evidence",str(e),"--permission-manifest",str(m),"--private-store-root",str(store)],cwd=ROOT,capture_output=True,text=True)
    T["private_external_bundle_pass"]=cp.returncode==0
    out=json.loads(cp.stdout) if cp.returncode==0 else {}
    T["stdout_redacts_raw_price_timestamp"]="66050" not in cp.stdout and "2026-09-08T08:50:00" not in cp.stdout and out.get("raw_evidence_not_printed") is True
    receipts=list((store/"quote_receipts").glob("*.json"))
    T["one_private_bundle_created"]=len(receipts)==1
    if receipts:
        bundle=json.loads(receipts[0].read_text())
        T["bundle_contains_private_raw_evidence"]=bundle["artifact_class"]=="JNU_PRIVATE_ENTITLED_QUOTE_BUNDLE" and bundle["raw_entitled_quote_evidence"]["price"]==66050 and bundle["public_distribution_permitted"] is False
        if os.name!="nt":T["private_file_mode_600"]=(receipts[0].stat().st_mode & 0o777)==0o600
        else:T["private_file_mode_600"]=True
    else:
        T["bundle_contains_private_raw_evidence"]=False;T["private_file_mode_600"]=False

    with tempfile.TemporaryDirectory(dir=ROOT,prefix=".jnu_bridge_inside_") as in0:
        inside=Path(in0);ie=inside/"e.json";ie.write_text(json.dumps(E))
        cp2=subprocess.run([PY,str(SCRIPT),"--evidence",str(ie),"--permission-manifest",str(m),"--private-store-root",str(store/"x")],cwd=ROOT,capture_output=True,text=True)
        T["repo_evidence_rejected"]=cp2.returncode!=0 and "outside the public repository" in cp2.stderr

    with tempfile.TemporaryDirectory(dir=ROOT,prefix=".jnu_bridge_store_") as s0:
        cp3=subprocess.run([PY,str(SCRIPT),"--evidence",str(e),"--permission-manifest",str(m),"--private-store-root",s0],cwd=ROOT,capture_output=True,text=True)
        T["repo_store_rejected"]=cp3.returncode!=0 and "outside the public repository" in cp3.stderr

    mpub=td/"manifest_public.json";xx=dict(M);xx["public_output_requested"]=True;xx["public_output_type"]="DERIVED_FORECAST";xx["public_publication_permission_status"]="EXPLICITLY_APPROVED";mpub.write_text(json.dumps(xx))
    cp4=subprocess.run([PY,str(SCRIPT),"--evidence",str(e),"--permission-manifest",str(mpub),"--private-store-root",str(store/"pub")],cwd=ROOT,capture_output=True,text=True)
    T["public_output_request_rejected"]=cp4.returncode!=0 and "prohibits public output requests" in cp4.stderr

    mcloud=td/"manifest_cloud.json";xx=dict(M);xx["third_party_cloud_processing_used"]=True;xx["third_party_cloud_permission_status"]="UNCONFIRMED";mcloud.write_text(json.dumps(xx))
    cp5=subprocess.run([PY,str(SCRIPT),"--evidence",str(e),"--permission-manifest",str(mcloud),"--private-store-root",str(store/"cloud")],cwd=ROOT,capture_output=True,text=True)
    T["unapproved_cloud_rejected"]=cp5.returncode!=0 and "explicit approval" in cp5.stderr

after=counts();T["real_ledger_untouched"]=before==after==(0,0)
status="PASS" if all(T.values()) else "FAIL";print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T),"real_ledger_before":before,"real_ledger_after":after},indent=2));raise SystemExit(0 if status=="PASS" else 1)
