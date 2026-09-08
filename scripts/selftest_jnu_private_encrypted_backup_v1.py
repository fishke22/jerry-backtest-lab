from __future__ import annotations
import json,os,shutil,subprocess,sys,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];PY=sys.executable
KEY=ROOT/"scripts"/"jnu_private_keyring_v1.py"
EEXP=ROOT/"scripts"/"export_jnu_private_encrypted_backupset_v1.py"
EIMP=ROOT/"scripts"/"import_jnu_private_encrypted_backupset_v1.py"
ROT=ROOT/"scripts"/"rotate_jnu_private_encrypted_backups_v1.py"
DRILL=ROOT/"scripts"/"run_jnu_private_encrypted_dr_drill_v1.py"
PREP=ROOT/"scripts"/"prepare_jnu_cloud_request_v1_1.py";BRIDGE=ROOT/"scripts"/"build_jnu_private_entitled_quote_bundle_v1.py";LAUNCH=ROOT/"scripts"/"launch_jnu_private_entitled_forecast_v1.py";OUT=ROOT/"scripts"/"record_jnu_private_entitled_outcome_v1.py";SCORE=ROOT/"scripts"/"score_jnu_private_entitled_live_shadow_v1.py"
RFD=ROOT/"live_shadow"/"forecasts";ROD=ROOT/"live_shadow"/"outcomes"
def counts():return (len(list(RFD.glob("*.json"))) if RFD.exists() else 0,len(list(ROD.glob("*.json"))) if ROD.exists() else 0)
def w(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n")
def draft():
 return {"draft_id":"JNU_DRAFT_20260907T080930_ENCBACKUP","analysis_frozen_at_taipei":"2026-09-07T08:09:30+08:00","symbol":"NK225MCU2026","target_day_session_date":"2026-09-07","decision_input":{"blocks":[{"id":"EXACT_JNU_PRICE_PATH","vote":"BEARISH","quality":"A","reason":"synthetic"},{"id":"DYNAMIC_PRICE_DISCOVERY","vote":"NEUTRAL","quality":"B","reason":"synthetic"},{"id":"CONTEMPORANEOUS_CROSS_MARKET","vote":"BEARISH","quality":"B","reason":"synthetic"},{"id":"POSITIONING_DERIVATIVES_CONTEXT","vote":"NEUTRAL","quality":"B","reason":"synthetic"}],"risk_modifiers":{"volatility_state":"UNKNOWN","event_state":"AUTO_OFFICIAL","sq_state":"UNKNOWN","post_event_exact_jnu_path_available":False}},"expected_path":"synthetic","key_levels":[65000],"invalidation_conditions":"synthetic","event_risk":"synthetic","flip_conditions":"synthetic","evidence_summary":"encrypted-backup"}
def event():
 checked="2026-09-07T08:09:45+08:00";names=["BOJ_RELEASE_SCHEDULE","JAPAN_STAT_CPI","JAPAN_STAT_LABOUR_FORCE","JAPAN_STAT_HOUSEHOLD_SPENDING","JAPAN_ESRI_GENERAL","JAPAN_ESRI_GDP","US_BLS_HIGH_IMPACT_SCHEDULE_COVERAGE","US_BEA_RELEASE_SCHEDULE","FEDERAL_RESERVE_CALENDAR"];src=[{"source":n,"reference":"https://official.example/"+n,"checked_at_taipei":checked,"http_status":200,"parsed_event_count":1} for n in names]
 return {"version":"1.1","status":"OFFICIAL_EVENT_STATE_READY","protocol":"config/jnu_official_event_state_protocol_v1_1.json","evaluated_at_taipei":checked,"target_day_session_date":"2026-09-07","event_state":"NORMAL","risk_state_evidence":{"checked_at_taipei":checked,"target_day_session_date":"2026-09-07","event_state":"NORMAL","volatility_state":"UNKNOWN","sq_state":"UNKNOWN","event_sources":src},"future_high_events":[],"past_high_events":[],"ambiguous_date_only_high_events":[],"source_failures":[],"all_parsed_events":[],"decision_risk_modifiers":{"volatility_state":"UNKNOWN","event_state":"NORMAL","sq_state":"UNKNOWN","post_event_exact_jnu_path_available":False},"real_registration_performed":False}
def ev(price,ts,obs):
 return {"entitlement_mode":"OSE_FREE_TRIAL","provider_name":"SYNTH","entitlement_reference":"opaque","transport_qualification_id":"q1","positive_margin_demonstrated":True,"canonical_symbol":"NK225MCU2026","exchange":"OSE","product":"Nikkei 225 micro Futures","contract_month":"2026-09","price":price,"tick_size":5,"provider_timestamp":ts,"observed_at_taipei":obs,"exact_product":True,"continuous_contract":False,"broker_login_used":False,"trading_permission_used":False,"order_capable_session_used":False,"identity_evidence":{"exchange":"OSE","product":"Nikkei 225 micro Futures","contract_month":"2026-09","provider_symbol":"MC225U26"},"storage_scope":"PRIVATE_INTERNAL_ONLY","evidence_destination_class":"PRIVATE_INTERNAL_STORE","raw_public_distribution_permitted":False,"public_derived_permission_status":"UNCONFIRMED","third_party_cloud_processing_used":False,"third_party_cloud_permission_status":"NOT_APPLICABLE"}
PM={"entitlement_mode":"OSE_FREE_TRIAL","raw_evidence_storage_scope":"PRIVATE_INTERNAL_ONLY","evidence_destination_class":"PRIVATE_INTERNAL_STORE","target_repository_visibility":"PRIVATE","raw_market_data_in_public_artifact":False,"third_party_cloud_processing_used":False,"third_party_cloud_permission_status":"NOT_APPLICABLE","public_output_requested":False,"public_output_type":"NONE","public_publication_permission_status":"UNCONFIRMED","reconstructive_market_data_fields_in_public_output":False}

before=counts();T={}
with tempfile.TemporaryDirectory(prefix="jnu_encbackup_ext_") as td0:
 td=Path(td0);ledger=td/"ledger";qstore=td/"qstore";launch=td/"launch.json";keyring=td/"keys"/"keyring.json";backuproot=td/"ebackups"
 LM={"version":"1.0","launch_id":"JNU_PRIV_LAUNCH_ENCBACKUP_20260908","mode":"SYNTHETIC","synthetic_data_only":True,"real_entitlement_connected":False,"private_ledger_root":str(ledger),"private_quote_store_root":str(qstore),"public_output_requested":False,"cloud_processing_used":False,"cloud_permission_status":"NOT_APPLICABLE","publication_permission_status":"UNCONFIRMED","retention_terms_status":"SYNTHETIC_TEST_ONLY","retention_policy_status":"SYNTHETIC_TEST_APPROVED","retention_days":30,"recovery_apply_allowed":True,"retention_quarantine_enabled":True,"permanent_purge_allowed":False};w(launch,LM)
 keyring.parent.mkdir(parents=True);cp=subprocess.run([PY,str(KEY),"init","--keyring",str(keyring),"--key-id","JNU_KEY_SYNTH_V1"],cwd=ROOT,capture_output=True,text=True);T["keyring_init_pass"]=cp.returncode==0 and "material_b64" not in cp.stdout
 if os.name!="nt":T["keyring_mode_600"]=(keyring.stat().st_mode & 0o777)==0o600
 else:T["keyring_mode_600"]=True
 dp=td/"d.json";ep=td/"e.json";rp=td/"request.json";w(dp,draft());w(ep,event());cp=subprocess.run([PY,str(PREP),"--draft",str(dp),"--output",str(rp),"--selftest","--event-evidence-file",str(ep),"--request-created-at-taipei","2026-09-07T08:10:00+08:00"],cwd=ROOT,capture_output=True,text=True);T["request_pass"]=cp.returncode==0
 pm=td/"pm.json";qe=td/"quote.json";w(pm,PM);w(qe,ev(65000,"2026-09-07T09:05:00+09:00","2026-09-07T08:05:30+08:00"));cp=subprocess.run([PY,str(BRIDGE),"--evidence",str(qe),"--permission-manifest",str(pm),"--private-store-root",str(qstore)],cwd=ROOT,capture_output=True,text=True);T["quote_bridge_pass"]=cp.returncode==0;qb=next((qstore/"quote_receipts").glob("*.json"))
 cp=subprocess.run([PY,str(LAUNCH),"--manifest",str(launch),"--request",str(rp),"--private-quote-bundle",str(qb),"--created-at-taipei","2026-09-07T08:10:30+08:00"],cwd=ROOT,capture_output=True,text=True);T["forecast_pass"]=cp.returncode==0;fid=json.loads(cp.stdout)["forecast_id"]
 ce=td/"close.json";w(ce,ev(64000,"2026-09-07T15:45:00+09:00","2026-09-07T14:45:30+08:00"));cp=subprocess.run([PY,str(OUT),"--private-ledger-root",str(ledger),"--forecast-id",fid,"--private-close-evidence",str(ce)],cwd=ROOT,capture_output=True,text=True);T["outcome_pass"]=cp.returncode==0
 cp=subprocess.run([PY,str(SCORE),"--private-ledger-root",str(ledger),"--output",str(ledger/"results"/"score.json")],cwd=ROOT,capture_output=True,text=True);T["score_pass"]=cp.returncode==0

 cp=subprocess.run([PY,str(EEXP),"--manifest",str(launch),"--keyring",str(keyring),"--destination-root",str(backuproot),"--backupset-id","JNU_PRIV_EBACKUP_SYNTH_001"],cwd=ROOT,capture_output=True,text=True);T["encrypted_export_pass"]=cp.returncode==0 and "material_b64" not in cp.stdout
 bs=backuproot/"JNU_PRIV_EBACKUP_SYNTH_001";bm=json.loads((bs/"manifest.json").read_text())
 T["manifest_has_no_key_material"]=bm["key_material_present"] is False and "material_b64" not in (bs/"manifest.json").read_text()
 payload=list((bs/"payload").glob("*.bin"));T["payload_ciphertext_only"]=len(payload)>0 and not list((bs/"payload").rglob("*.json"))

 auth=td/"restore.json";restore1=td/"restore1";A={"version":"1.0","restore_id":"JNU_PRIV_RESTORE_SYNTH_0001","mode":"SYNTHETIC","authorization_status":"EXPLICITLY_APPROVED_SYNTHETIC","backupset_id":"JNU_PRIV_EBACKUP_SYNTH_001","authorized_key_id":"JNU_KEY_SYNTH_V1","destination_ledger_root":str(restore1),"public_output_requested":False,"cloud_processing_used":False,"cloud_permission_status":"NOT_APPLICABLE","real_entitlement_connected":False};w(auth,A)
 cp=subprocess.run([PY,str(EIMP),"--backupset",str(bs),"--keyring",str(keyring),"--authorization",str(auth)],cwd=ROOT,capture_output=True,text=True);T["encrypted_import_pass"]=cp.returncode==0 and (restore1/"results"/"dr_revalidated_v1.json").exists()

 wrongring=td/"keys"/"wrong.json";cp=subprocess.run([PY,str(KEY),"init","--keyring",str(wrongring),"--key-id","JNU_KEY_SYNTH_V1"],cwd=ROOT,capture_output=True,text=True);wrongdest=td/"wrongdest";Aw=dict(A);Aw["restore_id"]="JNU_PRIV_RESTORE_SYNTH_0002";Aw["destination_ledger_root"]=str(wrongdest);aw=td/"wrongauth.json";w(aw,Aw);cp=subprocess.run([PY,str(EIMP),"--backupset",str(bs),"--keyring",str(wrongring),"--authorization",str(aw)],cwd=ROOT,capture_output=True,text=True);T["wrong_key_rejected"]=cp.returncode!=0 and not wrongdest.exists()

 tam=td/"tampered";shutil.copytree(bs,tam);pf=next((tam/"payload").glob("*.bin"));raw=bytearray(pf.read_bytes());raw[0]^=1;pf.write_bytes(bytes(raw));tdest=td/"tamdest";At=dict(A);At["restore_id"]="JNU_PRIV_RESTORE_SYNTH_0003";At["destination_ledger_root"]=str(tdest);ta=td/"tamauth.json";w(ta,At);cp=subprocess.run([PY,str(EIMP),"--backupset",str(tam),"--keyring",str(keyring),"--authorization",str(ta)],cwd=ROOT,capture_output=True,text=True);T["ciphertext_tamper_rejected"]=cp.returncode!=0 and not tdest.exists()

 cp=subprocess.run([PY,str(KEY),"rotate","--keyring",str(keyring),"--new-key-id","JNU_KEY_SYNTH_V2"],cwd=ROOT,capture_output=True,text=True);T["key_rotation_pass"]=cp.returncode==0 and "material_b64" not in cp.stdout
 cp=subprocess.run([PY,str(EEXP),"--manifest",str(launch),"--keyring",str(keyring),"--destination-root",str(backuproot),"--backupset-id","JNU_PRIV_EBACKUP_SYNTH_002"],cwd=ROOT,capture_output=True,text=True);T["new_backup_uses_rotated_key"]=cp.returncode==0 and json.loads((backuproot/"JNU_PRIV_EBACKUP_SYNTH_002"/"manifest.json").read_text())["key_id"]=="JNU_KEY_SYNTH_V2"
 olddest=td/"old_after_rotation";Ao=dict(A);Ao["restore_id"]="JNU_PRIV_RESTORE_SYNTH_0004";Ao["destination_ledger_root"]=str(olddest);ao=td/"oldauth.json";w(ao,Ao);cp=subprocess.run([PY,str(EIMP),"--backupset",str(bs),"--keyring",str(keyring),"--authorization",str(ao)],cwd=ROOT,capture_output=True,text=True);T["retired_key_restores_old_backup"]=cp.returncode==0

 cp=subprocess.run([PY,str(EEXP),"--manifest",str(launch),"--keyring",str(keyring),"--destination-root",str(backuproot),"--backupset-id","JNU_PRIV_EBACKUP_SYNTH_003"],cwd=ROOT,capture_output=True,text=True)
 cp=subprocess.run([PY,str(EEXP),"--manifest",str(launch),"--keyring",str(keyring),"--destination-root",str(backuproot),"--backupset-id","JNU_PRIV_EBACKUP_SYNTH_004"],cwd=ROOT,capture_output=True,text=True)
 cp=subprocess.run([PY,str(ROT),"--backup-root",str(backuproot),"--keep-generations","2","--apply"],cwd=ROOT,capture_output=True,text=True);ro=json.loads(cp.stdout) if cp.returncode==0 else {};T["backup_rotation_quarantine_pass"]=cp.returncode==0 and ro.get("active_generations")==2 and ro.get("quarantined_generations")==2 and ro.get("permanent_delete_performed") is False

 drill_auth=td/"drillauth.json";Ad=dict(A);Ad["restore_id"]="JNU_PRIV_RESTORE_SYNTH_DRILL";Ad["backupset_id"]="JNU_PRIV_EBACKUP_SYNTH_004";Ad["authorized_key_id"]="JNU_KEY_SYNTH_V2";Ad["destination_ledger_root"]=str(td/"placeholder");w(drill_auth,Ad)
 report=td/"drill_report.json";cp=subprocess.run([PY,str(DRILL),"--backupset",str(backuproot/"JNU_PRIV_EBACKUP_SYNTH_004"),"--keyring",str(keyring),"--authorization",str(drill_auth),"--drill-root",str(td/"drillroot"),"--report",str(report)],cwd=ROOT,capture_output=True,text=True);T["dr_drill_pass"]=cp.returncode==0 and report.exists()
 if report.exists():
  rr=json.loads(report.read_text());T["dr_objectives_measured"]=rr["integrity_status"]=="PASS" and rr["rto_objective_met"] is True and rr["backup_age_objective_met"] is True
 else:T["dr_objectives_measured"]=False
after=counts();T["public_ledger_untouched"]=before==after==(0,0)
status="PASS" if all(T.values()) else "FAIL";print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T),"public_ledger_before":before,"public_ledger_after":after},indent=2));raise SystemExit(0 if status=="PASS" else 1)
