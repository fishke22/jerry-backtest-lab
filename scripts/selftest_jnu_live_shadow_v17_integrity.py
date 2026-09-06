from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PY=sys.executable
PREP=ROOT/"scripts"/"prepare_jnu_cloud_request_v1.py"
PREFLIGHT=ROOT/"scripts"/"check_jnu_live_shadow_preflight_v1_1.py"
BUILDER=ROOT/"scripts"/"build_jnu_cloud_forecast_input_v1_1.py"
ATOMIC=ROOT/"scripts"/"register_jnu_operational_shadow_forecast_atomic_v3.py"
OUTCOME=ROOT/"scripts"/"record_jnu_operational_shadow_outcome_atomic_v2.py"
SCORER=ROOT/"scripts"/"score_jnu_operational_live_shadow_v1_5.py"
REAL_FD=ROOT/"live_shadow"/"forecasts"
REAL_OD=ROOT/"live_shadow"/"outcomes"

def run(cmd,check=True):
    return subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,check=check)

def write(path:Path,x:dict):
    path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def counts():
    return (
        len(list(REAL_FD.glob("*.json"))) if REAL_FD.exists() else 0,
        len(list(REAL_OD.glob("*.json"))) if REAL_OD.exists() else 0,
    )

def draft():
    return {
      "symbol":"NK225MCU2026",
      "target_day_session_date":"2026-09-07",
      "decision_input":{
        "blocks":[
          {"id":"EXACT_JNU_PRICE_PATH","vote":"BEARISH","quality":"A","reason":"synthetic exact path"},
          {"id":"DYNAMIC_PRICE_DISCOVERY","vote":"NEUTRAL","quality":"B","reason":"synthetic neutral"},
          {"id":"CONTEMPORANEOUS_CROSS_MARKET","vote":"BEARISH","quality":"B","reason":"synthetic cross"},
          {"id":"POSITIONING_DERIVATIVES_CONTEXT","vote":"NEUTRAL","quality":"B","reason":"synthetic neutral"}
        ],
        "risk_modifiers":{
          "volatility_state":"UNKNOWN","event_state":"AUTO_OFFICIAL","sq_state":"UNKNOWN",
          "post_event_exact_jnu_path_available":False
        }
      },
      "expected_path":"synthetic path",
      "key_levels":[65000],
      "invalidation_conditions":"synthetic invalidation",
      "event_risk":"official event state bound by preparation protocol",
      "flip_conditions":"synthetic flip",
      "evidence_summary":"synthetic v1.7 full-chain integrity selftest"
    }

def event_result():
    checked="2026-09-07T08:09:00+08:00"
    names=[
      "BOJ_RELEASE_SCHEDULE","JAPAN_STAT_CPI","JAPAN_STAT_LABOUR_FORCE",
      "JAPAN_STAT_HOUSEHOLD_SPENDING","JAPAN_ESRI_GENERAL","JAPAN_ESRI_GDP",
      "US_BLS_HIGH_IMPACT_SCHEDULE_COVERAGE","US_BEA_RELEASE_SCHEDULE",
      "FEDERAL_RESERVE_CALENDAR"
    ]
    sources=[
      {"source":n,"reference":f"https://official.example/{n}","checked_at_taipei":checked,
       "http_status":200,"parsed_event_count":1}
      for n in names
    ]
    return {
      "version":"1.1","status":"OFFICIAL_EVENT_STATE_READY",
      "protocol":"config/jnu_official_event_state_protocol_v1_1.json",
      "evaluated_at_taipei":checked,
      "target_day_session_date":"2026-09-07",
      "event_state":"NORMAL",
      "risk_state_evidence":{
        "checked_at_taipei":checked,"target_day_session_date":"2026-09-07",
        "event_state":"NORMAL","volatility_state":"UNKNOWN","sq_state":"UNKNOWN",
        "event_sources":sources
      },
      "future_high_events":[],"past_high_events":[],"ambiguous_date_only_high_events":[],
      "source_failures":[],"all_parsed_events":[],
      "decision_risk_modifiers":{
        "volatility_state":"UNKNOWN","event_state":"NORMAL","sq_state":"UNKNOWN",
        "post_event_exact_jnu_path_available":False
      },
      "real_registration_performed":False
    }

def quote():
    return {
      "source_id":"JPX_OSE_OFFICIAL","provider":"Japan Exchange Group / Osaka Exchange",
      "source_quality":"A","symbol":"NK225MCU2026","product":"Nikkei 225 micro Futures",
      "contract_month":"Sep.2026","contract_code":"115.2609/O","price":65000.0,
      "source_timestamp":"2026-09-07T08:05:00+08:00","freshness_age_seconds":300.0,
      "freshness_pass":True,"exact_product":True,"continuous_contract":False,
      "official_exchange_source":True
    }

def main():
    before=counts()
    if before!=(0,0):
        raise RuntimeError(f"v1.7 integrity selftest requires real ledger 0/0, got {before}")
    tests={}
    with tempfile.TemporaryDirectory(prefix="jnu_v17_integrity_") as td0:
        td=Path(td0)
        dp=td/"draft.json"; ep=td/"event.json"; rp=td/"request.json"; qp=td/"quote.json"
        write(dp,draft()); write(ep,event_result()); write(qp,quote())

        cp=run([PY,str(PREP),"--draft",str(dp),"--output",str(rp),"--selftest",
                "--event-evidence-file",str(ep),
                "--request-created-at-taipei","2026-09-07T08:10:00+08:00"],check=False)
        tests["prepared_request"]=cp.returncode==0 and rp.exists()

        cp=run([PY,str(PREFLIGHT),"--request",str(rp),"--quote",str(qp),
                "--now-taipei","2026-09-07T08:10:00+08:00",
                "--require-risk-evidence","--require-empty-real-ledger",
                "--output",str(td/"preflight.json")],check=False)
        tests["preflight_v11_ready"]=cp.returncode==0

        atomic=td/"atomic.json"
        cp=run([PY,str(BUILDER),"--request",str(rp),"--quote",str(qp),
                "--created-at-taipei","2026-09-07T08:10:00+08:00",
                "--output",str(atomic)],check=False)
        tests["builder_v11"]=cp.returncode==0

        fd=td/"forecasts"; od=td/"outcomes"
        cp=run([PY,str(ATOMIC),"--input",str(atomic),"--output-dir",str(fd)],check=False)
        tests["atomic_v3"]=cp.returncode==0
        reg=json.loads(cp.stdout); fid=reg["forecast_id"]
        forecast_path=fd/f"{fid}.json"
        f=json.loads(forecast_path.read_text(encoding="utf-8"))
        tests["forecast_preparation_bound"]=bool(
            f["request_preparation_validation"]["status"]=="PASS"
            and f["request_preparation_validation"]["official_event_source_coverage"]==9
            and f["risk_state_evidence_validation"]["official_event_provenance_verified"] is True
            and f["framework_sha256"] and f["shadow_prereg_sha256"] and f["implementation_sha256"]
        )

        run([PY,str(OUTCOME),"--forecast-id",fid,"--target-close-price","64000",
             "--target-close-timestamp","2026-09-07T15:45:00+09:00",
             "--target-close-source","synthetic exact Micro close","--exact-product",
             "--forecast-dir",str(fd),"--outcome-dir",str(od)])

        logical=forecast_path.read_bytes().replace(b"\r\n",b"\n").replace(b"\r",b"\n")
        forecast_path.write_bytes(logical)
        tests["forecast_converted_to_lf"]=b"\r\n" not in forecast_path.read_bytes()

        scorep=td/"score.json"
        cp=run([PY,str(SCORER),"--forecast-dir",str(fd),"--outcome-dir",str(od),
                "--output",str(scorep),"--selftest-untracked"],check=False)
        tests["scorer_v15_chain"]=cp.returncode==0
        score=json.loads(scorep.read_text(encoding="utf-8"))
        tests["scorer_recomputes_preparation"]=(
            score["version"]=="1.5"
            and score["integrity"]["status"]=="PASS"
            and score["integrity"]["prepared_request_recomputed"] is True
            and score["integrity"]["risk_state_evidence_recomputed"] is True
            and score["integrity"]["forecasts_verified"]==1
            and score["integrity"]["outcomes_verified"]==1
        )

        tamper=td/"tamper_forecasts"; shutil.copytree(fd,tamper)
        tp=tamper/f"{fid}.json"; tx=json.loads(tp.read_text(encoding="utf-8"))
        tx["request_preparation"]["protocol_sha256"]="0"*64
        write(tp,tx)
        cp=run([PY,str(SCORER),"--forecast-dir",str(tamper),"--outcome-dir",str(od),
                "--output",str(td/"tamper_prep_score.json"),"--selftest-untracked"],check=False)
        tests["preparation_tamper_rejected"]=(
            cp.returncode!=0 and "request_preparation protocol SHA mismatch" in cp.stderr
        )

        tamper2=td/"tamper2_forecasts"; shutil.copytree(fd,tamper2)
        tp2=tamper2/f"{fid}.json"; tx2=json.loads(tp2.read_text(encoding="utf-8"))
        tx2["risk_state_evidence"]["event_state_protocol_sha256"]="f"*64
        write(tp2,tx2)
        cp=run([PY,str(SCORER),"--forecast-dir",str(tamper2),"--outcome-dir",str(od),
                "--output",str(td/"tamper_event_score.json"),"--selftest-untracked"],check=False)
        tests["event_protocol_tamper_rejected"]=(
            cp.returncode!=0 and "event-state protocol SHA mismatch" in cp.stderr
        )

        tamper3=td/"tamper3_forecasts"; shutil.copytree(fd,tamper3)
        tp3=tamper3/f"{fid}.json"; tx3=json.loads(tp3.read_text(encoding="utf-8"))
        tx3["risk_state_evidence"]["event_sources"]=tx3["risk_state_evidence"]["event_sources"][:-1]
        tx3["risk_state_evidence"]["observed_event_source_coverage"]=8
        write(tp3,tx3)
        cp=run([PY,str(SCORER),"--forecast-dir",str(tamper3),"--outcome-dir",str(od),
                "--output",str(td/"tamper_coverage_score.json"),"--selftest-untracked"],check=False)
        tests["source_coverage_tamper_rejected"]=(
            cp.returncode!=0 and "official event source coverage mismatch" in cp.stderr
        )

    after=counts()
    tests["real_ledger_untouched"]=before==after==(0,0)
    status="PASS" if all(tests.values()) else "FAIL"
    print(json.dumps({"status":status,"tests":tests,"real_ledger_before":before,"real_ledger_after":after},
                     ensure_ascii=False,indent=2))
    raise SystemExit(0 if status=="PASS" else 1)

if __name__=="__main__":
    main()
