from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PY=sys.executable
PREP=ROOT/"scripts"/"prepare_jnu_cloud_request_v1_1.py";BRIDGE=ROOT/"scripts"/"build_jnu_private_entitled_quote_bundle_v1.py"
FORECAST=ROOT/"scripts"/"register_jnu_private_entitled_forecast_v1.py";OUTCOME=ROOT/"scripts"/"record_jnu_private_entitled_outcome_v1.py";SCORER=ROOT/"scripts"/"score_jnu_private_entitled_live_shadow_v1.py"
RFD=ROOT/"live_shadow"/"forecasts";ROD=ROOT/"live_shadow"/"outcomes"
def counts():return (len(list(RFD.glob("*.json"))) if RFD.exists() else 0,len(list(ROD.glob("*.json"))) if ROD.exists() else 0)
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def draft():
    return {"draft_id":"JNU_DRAFT_20260907T080930_PRIVSELF","analysis_frozen_at_taipei":"2026-09-07T08:09:30+08:00","symbol":"NK225MCU2026","target_day_session_date":"2026-09-07",
      "decision_input":{"blocks":[{"id":"EXACT_JNU_PRICE_PATH","vote":"BEARISH","quality":"A","reason":"synthetic exact path"},{"id":"DYNAMIC_PRICE_DISCOVERY","vote":"NEUTRAL","quality":"B","reason":"synthetic neutral"},{"id":"CONTEMPORANEOUS_CROSS_MARKET","vote":"BEARISH","quality":"B","reason":"synthetic cross"},{"id":"POSITIONING_DERIVATIVES_CONTEXT","vote":"NEUTRAL","quality":"B","reason":"synthetic neutral"}],"risk_modifiers":{"volatility_state":"UNKNOWN","event_state":"AUTO_OFFICIAL","sq_state":"UNKNOWN","post_event_exact_jnu_path_available":False}},
      "expected_path":"synthetic private path","key_levels":[65000],"invalidation_conditions":"synthetic invalidation","event_risk":"official event state bound by preparer","flip_conditions":"synthetic flip","evidence_summary":"synthetic private entitled ledger selftest"}
def event_result():
    checked="2026-09-07T08:09:45+08:00";names=["BOJ_RELEASE_SCHEDULE","JAPAN_STAT_CPI","JAPAN_STAT_LABOUR_FORCE","JAPAN_STAT_HOUSEHOLD_SPENDING","JAPAN_ESRI_GENERAL","JAPAN_ESRI_GDP","US_BLS_HIGH_IMPACT_SCHEDULE_COVERAGE","US_BEA_RELEASE_SCHEDULE","FEDERAL_RESERVE_CALENDAR"]
    sources=[{"source":n,"reference":f"https://official.example/{n}","checked_at_taipei":checked,"http_status":200,"parsed_event_count":1} for n in names]
    return {"version":"1.1","status":"OFFICIAL_EVENT_STATE_READY","protocol":"config/jnu_official_event_state_protocol_v1_1.json","evaluated_at_taipei":checked,"target_day_session_date":"2026-09-07","event_state":"NORMAL","risk_state_evidence":{"checked_at_taipei":checked,"target_day_session_date":"2026-09-07","event_state":"NORMAL","volatility_state":"UNKNOWN","sq_state":"UNKNOWN","event_sources":sources},"future_high_events":[],"past_high_events":[],"ambiguous_date_only_high_events":[],"source_failures":[],"all_parsed_events":[],"decision_risk_modifiers":{"volatility_state":"UNKNOWN","event_state":"NORMAL","sq_state":"UNKNOWN","post_event_exact_jnu_path_available":False},"real_registration_performed":False}
def ev(price,pt,obs):
    return {"entitlement_mode":"OSE_FREE_TRIAL","provider_name":"SYNTH","entitlement_reference":"opaque","transport_qualification_id":"q1","positive_margin_demonstrated":True,"canonical_symbol":"NK225MCU2026","exchange":"OSE","product":"Nikkei 225 micro Futures","contract_month":"2026-09","price":price,"tick_size":5,"provider_timestamp":pt,"observed_at_taipei":obs,"exact_product":True,"continuous_contract":False,"broker_login_used":False,"trading_permission_used":False,"order_capable_session_used":False,"identity_evidence":{"exchange":"OSE","product":"Nikkei 225 micro Futures","contract_month":"2026-09","provider_symbol":"MC225U26"},"storage_scope":"PRIVATE_INTERNAL_ONLY","evidence_destination_class":"PRIVATE_INTERNAL_STORE","raw_public_distribution_permitted":False,"public_derived_permission_status":"UNCONFIRMED","third_party_cloud_processing_used":False,"third_party_cloud_permission_status":"NOT_APPLICABLE"}
M={"entitlement_mode":"OSE_FREE_TRIAL","raw_evidence_storage_scope":"PRIVATE_INTERNAL_ONLY","evidence_destination_class":"PRIVATE_INTERNAL_STORE","target_repository_visibility":"PRIVATE","raw_market_data_in_public_artifact":False,"third_party_cloud_processing_used":False,"third_party_cloud_permission_status":"NOT_APPLICABLE","public_output_requested":False,"public_output_type":"NONE","public_publication_permission_status":"UNCONFIRMED","reconstructive_market_data_fields_in_public_output":False}
before=counts();T={}
with tempfile.TemporaryDirectory(prefix="jnu_private_ledger_ext_") as td0:
    td=Path(td0);dp=td/"draft.json";ep=td/"event.json";rp=td/"request.json";write(dp,draft());write(ep,event_result())
    cp=subprocess.run([PY,str(PREP),"--draft",str(dp),"--output",str(rp),"--selftest","--event-evidence-file",str(ep),"--request-created-at-taipei","2026-09-07T08:10:00+08:00"],cwd=ROOT,capture_output=True,text=True);T["prepared_request_pass"]=cp.returncode==0
    qe=td/"quote.json";pm=td/"manifest.json";store=td/"quote_store";write(qe,ev(65000,"2026-09-07T09:05:00+09:00","2026-09-07T08:05:30+08:00"));write(pm,M)
    cp=subprocess.run([PY,str(BRIDGE),"--evidence",str(qe),"--permission-manifest",str(pm),"--private-store-root",str(store)],cwd=ROOT,capture_output=True,text=True);T["private_quote_bridge_pass"]=cp.returncode==0
    receipts=list((store/"quote_receipts").glob("*.json"));qb=receipts[0] if len(receipts)==1 else Path("missing")
    ledger=td/"ledger"
    cp=subprocess.run([PY,str(FORECAST),"--request",str(rp),"--private-quote-bundle",str(qb),"--private-ledger-root",str(ledger),"--created-at-taipei","2026-09-07T08:10:30+08:00"],cwd=ROOT,capture_output=True,text=True);T["private_forecast_pass"]=cp.returncode==0
    fo=json.loads(cp.stdout) if cp.returncode==0 else {};fid=fo.get("forecast_id","")
    T["forecast_stdout_redacted"]="65000" not in cp.stdout and "BEARISH" not in cp.stdout and "LOW" not in cp.stdout and fo.get("raw_and_derived_fields_not_printed") is True
    fps=list((ledger/"forecasts").glob("*.json"));T["one_private_forecast"]=len(fps)==1
    if fps:
        f=json.loads(fps[0].read_text());T["forecast_private_and_v19"]=f["storage_scope"]=="PRIVATE_INTERNAL_ONLY" and f["framework_sha256"]==__import__("jnu_integrity_hash_v1").canonical_text_sha256(ROOT/"config"/"jnu_operational_framework_current_v1_9.json")
        T["forecast_mode_600"]=True if os.name=="nt" else (fps[0].stat().st_mode & 0o777)==0o600
    else:T["forecast_private_and_v19"]=False;T["forecast_mode_600"]=False
    ce=td/"close.json";write(ce,ev(64000,"2026-09-07T15:45:00+09:00","2026-09-07T14:45:30+08:00"))
    cp=subprocess.run([PY,str(OUTCOME),"--private-ledger-root",str(ledger),"--forecast-id",fid,"--private-close-evidence",str(ce)],cwd=ROOT,capture_output=True,text=True);T["private_outcome_pass"]=cp.returncode==0
    T["outcome_stdout_redacted"]="64000" not in cp.stdout and "return" not in cp.stdout.lower() and "hit" not in cp.stdout.lower()
    op=ledger/"outcomes"/f"{fid}.json";T["private_outcome_created"]=op.exists()
    scorep=ledger/"results"/"score.json";cp=subprocess.run([PY,str(SCORER),"--private-ledger-root",str(ledger),"--output",str(scorep)],cwd=ROOT,capture_output=True,text=True);T["private_scorer_pass"]=cp.returncode==0 and scorep.exists()
    T["scorer_stdout_redacted"]="accuracy" not in cp.stdout.lower() and "mean_signed" not in cp.stdout.lower() and "BEARISH" not in cp.stdout
    if scorep.exists():
        s=json.loads(scorep.read_text());T["private_score_integrity"]=s["integrity"]["status"]=="PASS" and s["forecast_records"]==1 and s["outcomes_recorded"]==1 and s["storage_scope"]=="PRIVATE_INTERNAL_ONLY"
    else:T["private_score_integrity"]=False
    with tempfile.TemporaryDirectory(dir=ROOT,prefix=".jnu_private_ledger_inside_") as inside:
        cp=subprocess.run([PY,str(FORECAST),"--request",str(rp),"--private-quote-bundle",str(qb),"--private-ledger-root",inside,"--created-at-taipei","2026-09-07T08:10:30+08:00"],cwd=ROOT,capture_output=True,text=True);T["repo_ledger_rejected"]=cp.returncode!=0 and "outside the public repository" in cp.stderr
    if fps:
        tam=td/"tamledger";shutil.copytree(ledger,tam);tf=next((tam/"forecasts").glob("*.json"));x=json.loads(tf.read_text());x["reference_price"]=65100;write(tf,x)
        cp=subprocess.run([PY,str(SCORER),"--private-ledger-root",str(tam),"--output",str(tam/"results"/"tam.json")],cwd=ROOT,capture_output=True,text=True);T["forecast_tamper_rejected"]=cp.returncode!=0
after=counts();T["public_real_ledger_untouched"]=before==after==(0,0)
status="PASS" if all(T.values()) else "FAIL";print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T),"public_real_ledger_before":before,"public_real_ledger_after":after},indent=2));raise SystemExit(0 if status=="PASS" else 1)
