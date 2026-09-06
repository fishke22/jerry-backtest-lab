from __future__ import annotations

import json
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
      "event_risk":"event state is bound by official preparer",
      "flip_conditions":"synthetic flip",
      "evidence_summary":"synthetic request-preparation selftest"
    }

def event_result(state="NORMAL",checked="2026-09-07T08:09:00+08:00"):
    sources=[]
    names=[
      "BOJ_RELEASE_SCHEDULE","JAPAN_STAT_CPI","JAPAN_STAT_LABOUR_FORCE",
      "JAPAN_STAT_HOUSEHOLD_SPENDING","JAPAN_ESRI_GENERAL","JAPAN_ESRI_GDP",
      "US_BLS_HIGH_IMPACT_SCHEDULE_COVERAGE","US_BEA_RELEASE_SCHEDULE",
      "FEDERAL_RESERVE_CALENDAR"
    ]
    for n in names:
        sources.append({
          "source":n,"reference":f"https://official.example/{n}",
          "checked_at_taipei":checked,"http_status":200,"parsed_event_count":1
        })
    e={
      "checked_at_taipei":checked,
      "target_day_session_date":"2026-09-07",
      "event_state":state,"volatility_state":"UNKNOWN","sq_state":"UNKNOWN",
      "event_sources":sources
    }
    if state=="UNKNOWN":
        e["event_unavailability_reason"]="synthetic unavailable"
    return {
      "version":"1.1",
      "status":"OFFICIAL_EVENT_STATE_READY" if state!="UNKNOWN" else "OFFICIAL_EVENT_STATE_FAIL_CLOSED_UNKNOWN",
      "protocol":"config/jnu_official_event_state_protocol_v1_1.json",
      "evaluated_at_taipei":checked,
      "target_day_session_date":"2026-09-07",
      "event_state":state,
      "risk_state_evidence":e,
      "future_high_events":[],"past_high_events":[],"ambiguous_date_only_high_events":[],
      "source_failures":[] if state!="UNKNOWN" else [{"source_id":"X","error":"synthetic"}],
      "all_parsed_events":[],
      "decision_risk_modifiers":{
        "volatility_state":"UNKNOWN","event_state":state,"sq_state":"UNKNOWN",
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
        raise RuntimeError(f"pre-first preparation selftest requires real ledger 0/0, got {before}")
    tests={}
    with tempfile.TemporaryDirectory(prefix="jnu_prepare_selftest_") as td0:
        td=Path(td0)
        dp=td/"draft.json"; ep=td/"event.json"; rp=td/"request.json"
        write(dp,draft()); write(ep,event_result())

        cp=run([PY,str(PREP),"--draft",str(dp),"--output",str(rp),"--selftest",
                "--event-evidence-file",str(ep),
                "--request-created-at-taipei","2026-09-07T08:10:00+08:00"],check=False)
        tests["prepare_known_event"]=cp.returncode==0 and rp.exists()
        req=json.loads(rp.read_text(encoding="utf-8"))
        tests["request_bound_provenance"]=(
            req["decision_input"]["risk_modifiers"]["event_state"]=="NORMAL"
            and req["risk_state_evidence"]["event_state"]=="NORMAL"
            and req["risk_state_evidence"]["required_event_source_coverage"]==9
            and req["risk_state_evidence"]["observed_event_source_coverage"]==9
            and req["request_preparation"]["real_registration_performed"] is False
        )
        lifetime=(
          __import__("datetime").datetime.fromisoformat(req["request_valid_until_taipei"])
          - __import__("datetime").datetime.fromisoformat(req["request_created_at_taipei"])
        ).total_seconds()
        tests["request_exact_900s_window"]=lifetime==900

        qp=td/"quote.json"; write(qp,quote())
        cp=run([PY,str(PREFLIGHT),"--request",str(rp),"--quote",str(qp),
                "--now-taipei","2026-09-07T08:10:00+08:00",
                "--require-risk-evidence","--require-empty-real-ledger",
                "--output",str(td/"preflight.json")],check=False)
        tests["preflight_ready"]=cp.returncode==0

        atomic=td/"atomic.json"
        cp=run([PY,str(BUILDER),"--request",str(rp),"--quote",str(qp),
                "--created-at-taipei","2026-09-07T08:10:00+08:00",
                "--output",str(atomic)],check=False)
        tests["builder_accepts_prepared_request"]=cp.returncode==0
        fd=td/"forecasts"
        cp=run([PY,str(ATOMIC),"--input",str(atomic),"--output-dir",str(fd)],check=False)
        tests["atomic_temp_registration"]=cp.returncode==0 and len(list(fd.glob("*.json")))==1

        unknown=td/"event_unknown.json"; write(unknown,event_result("UNKNOWN"))
        cp=run([PY,str(PREP),"--draft",str(dp),"--output",str(td/"unknown_req.json"),"--selftest",
                "--event-evidence-file",str(unknown),
                "--request-created-at-taipei","2026-09-07T08:10:00+08:00"],check=False)
        tests["unknown_event_rejected"]=cp.returncode!=0 and "event_state UNKNOWN" in cp.stderr

        stale=td/"event_stale.json"; write(stale,event_result("NORMAL","2026-09-07T07:54:00+08:00"))
        cp=run([PY,str(PREP),"--draft",str(dp),"--output",str(td/"stale_req.json"),"--selftest",
                "--event-evidence-file",str(stale),
                "--request-created-at-taipei","2026-09-07T08:10:00+08:00"],check=False)
        tests["stale_event_rejected"]=cp.returncode!=0 and "too old" in cp.stderr

        manual=draft(); manual["decision_input"]["risk_modifiers"]["event_state"]="NORMAL"
        mp=td/"manual.json"; write(mp,manual)
        cp=run([PY,str(PREP),"--draft",str(mp),"--output",str(td/"manual_req.json"),"--selftest",
                "--event-evidence-file",str(ep),
                "--request-created-at-taipei","2026-09-07T08:10:00+08:00"],check=False)
        tests["manual_event_state_rejected"]=cp.returncode!=0 and "AUTO_OFFICIAL" in cp.stderr

        forbidden=draft(); forbidden["risk_state_evidence"]={}
        fp=td/"forbidden.json"; write(fp,forbidden)
        cp=run([PY,str(PREP),"--draft",str(fp),"--output",str(td/"forbidden_req.json"),"--selftest",
                "--event-evidence-file",str(ep),
                "--request-created-at-taipei","2026-09-07T08:10:00+08:00"],check=False)
        tests["handcrafted_risk_evidence_rejected"]=cp.returncode!=0 and "preparer owns" in cp.stderr

        cp=run([PY,str(PREP),"--draft",str(dp),"--output",str(td/"illegal_override.json"),
                "--event-evidence-file",str(ep)],check=False)
        tests["real_mode_synthetic_override_rejected"]=cp.returncode!=0 and "selftest-only" in cp.stderr

    after=counts()
    tests["real_ledger_untouched"]=before==after==(0,0)
    status="PASS" if all(tests.values()) else "FAIL"
    print(json.dumps({"status":status,"tests":tests,"real_ledger_before":before,"real_ledger_after":after},
                     ensure_ascii=False,indent=2))
    raise SystemExit(0 if status=="PASS" else 1)

if __name__=="__main__":
    main()
