from __future__ import annotations
import json, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PY=sys.executable
PREP=ROOT/"scripts"/"prepare_jnu_cloud_request_v1_1.py"
PREFLIGHT=ROOT/"scripts"/"check_jnu_live_shadow_preflight_v1_2.py"
BUILDER=ROOT/"scripts"/"build_jnu_cloud_forecast_input_v1_2.py"
ATOMIC=ROOT/"scripts"/"register_jnu_operational_shadow_forecast_atomic_v4.py"
OUTCOME=ROOT/"scripts"/"record_jnu_operational_shadow_outcome_atomic_v2.py"
SCORER=ROOT/"scripts"/"score_jnu_operational_live_shadow_v1_6.py"
REAL_FD=ROOT/"live_shadow"/"forecasts"; REAL_OD=ROOT/"live_shadow"/"outcomes"

def run(cmd,check=True):
    return subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,check=check)
def write(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def counts():
    return (len(list(REAL_FD.glob("*.json"))) if REAL_FD.exists() else 0,
            len(list(REAL_OD.glob("*.json"))) if REAL_OD.exists() else 0)

def draft(analysis="2026-09-07T08:09:30+08:00"):
    return {
      "draft_id":"JNU_DRAFT_20260907T080930_SELFTEST",
      "analysis_frozen_at_taipei":analysis,
      "symbol":"NK225MCU2026","target_day_session_date":"2026-09-07",
      "decision_input":{
        "blocks":[
          {"id":"EXACT_JNU_PRICE_PATH","vote":"BEARISH","quality":"A","reason":"synthetic exact path"},
          {"id":"DYNAMIC_PRICE_DISCOVERY","vote":"NEUTRAL","quality":"B","reason":"synthetic neutral"},
          {"id":"CONTEMPORANEOUS_CROSS_MARKET","vote":"BEARISH","quality":"B","reason":"synthetic cross"},
          {"id":"POSITIONING_DERIVATIVES_CONTEXT","vote":"NEUTRAL","quality":"B","reason":"synthetic neutral"}],
        "risk_modifiers":{"volatility_state":"UNKNOWN","event_state":"AUTO_OFFICIAL","sq_state":"UNKNOWN",
                          "post_event_exact_jnu_path_available":False}},
      "expected_path":"synthetic path","key_levels":[65000],
      "invalidation_conditions":"synthetic invalidation",
      "event_risk":"official event state bound by preparer",
      "flip_conditions":"synthetic flip",
      "evidence_summary":"synthetic v1.8 analysis-fresh full-chain integrity selftest"}

def event_result():
    checked="2026-09-07T08:09:45+08:00"
    names=["BOJ_RELEASE_SCHEDULE","JAPAN_STAT_CPI","JAPAN_STAT_LABOUR_FORCE",
           "JAPAN_STAT_HOUSEHOLD_SPENDING","JAPAN_ESRI_GENERAL","JAPAN_ESRI_GDP",
           "US_BLS_HIGH_IMPACT_SCHEDULE_COVERAGE","US_BEA_RELEASE_SCHEDULE","FEDERAL_RESERVE_CALENDAR"]
    sources=[{"source":n,"reference":f"https://official.example/{n}","checked_at_taipei":checked,
              "http_status":200,"parsed_event_count":1} for n in names]
    return {"version":"1.1","status":"OFFICIAL_EVENT_STATE_READY",
      "protocol":"config/jnu_official_event_state_protocol_v1_1.json",
      "evaluated_at_taipei":checked,"target_day_session_date":"2026-09-07","event_state":"NORMAL",
      "risk_state_evidence":{"checked_at_taipei":checked,"target_day_session_date":"2026-09-07",
        "event_state":"NORMAL","volatility_state":"UNKNOWN","sq_state":"UNKNOWN","event_sources":sources},
      "future_high_events":[],"past_high_events":[],"ambiguous_date_only_high_events":[],
      "source_failures":[],"all_parsed_events":[],
      "decision_risk_modifiers":{"volatility_state":"UNKNOWN","event_state":"NORMAL","sq_state":"UNKNOWN",
                                 "post_event_exact_jnu_path_available":False},
      "real_registration_performed":False}

def quote():
    return {"source_id":"JPX_OSE_OFFICIAL","provider":"Japan Exchange Group / Osaka Exchange",
      "source_quality":"A","symbol":"NK225MCU2026","product":"Nikkei 225 micro Futures",
      "contract_month":"Sep.2026","contract_code":"115.2609/O","price":65000.0,
      "source_timestamp":"2026-09-07T08:05:00+08:00","freshness_age_seconds":300.0,
      "freshness_pass":True,"exact_product":True,"continuous_contract":False,"official_exchange_source":True}

def main():
    before=counts()
    if before!=(0,0): raise RuntimeError(f"v1.8 selftest requires real ledger 0/0, got {before}")
    tests={}
    with tempfile.TemporaryDirectory(prefix="jnu_v18_") as td0:
        td=Path(td0); dp=td/"draft.json"; ep=td/"event.json"; rp=td/"request.json"; qp=td/"quote.json"
        write(dp,draft()); write(ep,event_result()); write(qp,quote())
        cp=run([PY,str(PREP),"--draft",str(dp),"--output",str(rp),"--selftest",
                "--event-evidence-file",str(ep),"--request-created-at-taipei","2026-09-07T08:10:00+08:00"],check=False)
        tests["fresh_analysis_prepared"]=cp.returncode==0 and rp.exists()
        req=json.loads(rp.read_text(encoding="utf-8"))
        tests["analysis_binding"]=(
          req["draft_id"]=="JNU_DRAFT_20260907T080930_SELFTEST"
          and req["analysis_frozen_at_taipei"]=="2026-09-07T08:09:30+08:00"
          and req["request_preparation"]["analysis_age_at_request_seconds"]==30.0
          and req["request_preparation"]["draft_protocol"]=="config/jnu_cloud_request_draft_protocol_v1.json")

        stale=td/"stale.json"; write(stale,draft("2026-09-07T07:54:59+08:00"))
        cp=run([PY,str(PREP),"--draft",str(stale),"--output",str(td/"stale_req.json"),"--selftest",
                "--event-evidence-file",str(ep),"--request-created-at-taipei","2026-09-07T08:10:00+08:00"],check=False)
        tests["stale_analysis_rejected"]=cp.returncode!=0 and "analysis draft freshness exceeds 900 seconds" in cp.stderr

        future=td/"future.json"; write(future,draft("2026-09-07T08:10:01+08:00"))
        cp=run([PY,str(PREP),"--draft",str(future),"--output",str(td/"future_req.json"),"--selftest",
                "--event-evidence-file",str(ep),"--request-created-at-taipei","2026-09-07T08:10:00+08:00"],check=False)
        tests["future_analysis_rejected"]=cp.returncode!=0 and "analysis draft freshness exceeds 900 seconds" in cp.stderr

        cp=run([PY,str(PREFLIGHT),"--request",str(rp),"--quote",str(qp),
                "--now-taipei","2026-09-07T08:10:00+08:00","--require-risk-evidence",
                "--require-empty-real-ledger","--output",str(td/"preflight.json")],check=False)
        tests["preflight_v12"]=cp.returncode==0
        atomic=td/"atomic.json"
        cp=run([PY,str(BUILDER),"--request",str(rp),"--quote",str(qp),
                "--created-at-taipei","2026-09-07T08:10:00+08:00","--output",str(atomic)],check=False)
        tests["builder_v12"]=cp.returncode==0

        fd=td/"forecasts"; od=td/"outcomes"
        cp=run([PY,str(ATOMIC),"--input",str(atomic),"--output-dir",str(fd)],check=False)
        tests["atomic_v4"]=cp.returncode==0
        reg=json.loads(cp.stdout); fid=reg["forecast_id"]; fp=fd/f"{fid}.json"
        f=json.loads(fp.read_text(encoding="utf-8"))
        tests["forecast_analysis_bound"]=(
          f["request_preparation_validation"]["analysis_age_at_request_seconds"]==30.0
          and f["analysis_draft_protocol_sha256"]
          and f["draft_id"]==req["draft_id"])

        run([PY,str(OUTCOME),"--forecast-id",fid,"--target-close-price","64000",
             "--target-close-timestamp","2026-09-07T15:45:00+09:00",
             "--target-close-source","synthetic exact Micro close","--exact-product",
             "--forecast-dir",str(fd),"--outcome-dir",str(od)])
        logical=fp.read_bytes().replace(b"\r\n",b"\n").replace(b"\r",b"\n"); fp.write_bytes(logical)
        scorep=td/"score.json"
        cp=run([PY,str(SCORER),"--forecast-dir",str(fd),"--outcome-dir",str(od),
                "--output",str(scorep),"--selftest-untracked"],check=False)
        tests["scorer_v16"]=cp.returncode==0
        score=json.loads(scorep.read_text(encoding="utf-8"))
        tests["scorer_recomputes_analysis"]=(
          score["version"]=="1.6" and score["integrity"]["analysis_draft_recomputed"] is True
          and score["integrity"]["forecasts_verified"]==1 and score["integrity"]["outcomes_verified"]==1)

        tam=td/"tam"; shutil.copytree(fd,tam); tp=tam/f"{fid}.json"; tx=json.loads(tp.read_text(encoding="utf-8"))
        tx["analysis_frozen_at_taipei"]="2026-09-07T07:00:00+08:00"; write(tp,tx)
        cp=run([PY,str(SCORER),"--forecast-dir",str(tam),"--outcome-dir",str(od),
                "--output",str(td/"tam_score.json"),"--selftest-untracked"],check=False)
        tests["analysis_timestamp_tamper_rejected"]=cp.returncode!=0 and "analysis draft freshness exceeds 900 seconds" in cp.stderr

        tam2=td/"tam2"; shutil.copytree(fd,tam2); tp2=tam2/f"{fid}.json"; tx2=json.loads(tp2.read_text(encoding="utf-8"))
        tx2["request_preparation"]["draft_protocol_sha256"]="0"*64; write(tp2,tx2)
        cp=run([PY,str(SCORER),"--forecast-dir",str(tam2),"--outcome-dir",str(od),
                "--output",str(td/"tam2_score.json"),"--selftest-untracked"],check=False)
        tests["draft_protocol_tamper_rejected"]=cp.returncode!=0 and "draft protocol SHA mismatch" in cp.stderr

    after=counts(); tests["real_ledger_untouched"]=before==after==(0,0)
    status="PASS" if all(bool(x) for x in tests.values()) else "FAIL"
    print(json.dumps({"status":status,"tests":tests,"real_ledger_before":before,"real_ledger_after":after},
                     ensure_ascii=False,indent=2))
    raise SystemExit(0 if status=="PASS" else 1)
if __name__=="__main__": main()
