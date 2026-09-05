from __future__ import annotations
import copy, json, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PREFLIGHT=ROOT/"scripts"/"check_jnu_live_shadow_preflight_v1.py"
REAL_FD=ROOT/"live_shadow"/"forecasts"
REAL_OD=ROOT/"live_shadow"/"outcomes"

def ledger_counts():
    return (
        len(list(REAL_FD.glob("*.json"))) if REAL_FD.exists() else 0,
        len(list(REAL_OD.glob("*.json"))) if REAL_OD.exists() else 0,
    )

def run_case(td:Path,name:str,req:dict,quote:dict,now:str):
    rp=td/f"{name}_request.json"; qp=td/f"{name}_quote.json"; op=td/f"{name}_result.json"
    rp.write_text(json.dumps(req,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    qp.write_text(json.dumps(quote,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    cp=subprocess.run([
        sys.executable,str(PREFLIGHT),"--request",str(rp),"--quote",str(qp),
        "--now-taipei",now,"--require-empty-real-ledger","--require-risk-evidence",
        "--output",str(op)
    ],cwd=ROOT,capture_output=True,text=True)
    result=json.loads(op.read_text(encoding="utf-8"))
    return cp.returncode,result
def base_request():
    return {
      "request_id":"JNU_REQ_PREFLIGHT_SELFTEST",
      "request_created_at_taipei":"2026-09-07T08:10:00+08:00",
      "request_valid_until_taipei":"2026-09-07T08:25:00+08:00",
      "symbol":"NK225MCU2026","target_day_session_date":"2026-09-07",
      "decision_input":{
        "blocks":[
          {"id":"EXACT_JNU_PRICE_PATH","vote":"UNAVAILABLE","quality":"C","reason":"selftest"},
          {"id":"DYNAMIC_PRICE_DISCOVERY","vote":"BULLISH","quality":"B","reason":"selftest"},
          {"id":"CONTEMPORANEOUS_CROSS_MARKET","vote":"BULLISH","quality":"B","reason":"selftest"},
          {"id":"POSITIONING_DERIVATIVES_CONTEXT","vote":"UNAVAILABLE","quality":"C","reason":"selftest"}
        ],
        "risk_modifiers":{"volatility_state":"UNKNOWN","event_state":"NORMAL","sq_state":"UNKNOWN",
                          "post_event_exact_jnu_path_available":False}
      },
      "risk_state_evidence":{"checked_at_taipei":"2026-09-07T08:05:00+08:00",
        "target_day_session_date":"2026-09-07",
        "event_state":"NORMAL","volatility_state":"UNKNOWN","sq_state":"UNKNOWN",
        "event_sources":[{"source":"synthetic official calendar","reference":"selftest",
                          "checked_at_taipei":"2026-09-07T08:05:00+08:00"}]},
      "expected_path":"selftest","key_levels":[65000],"invalidation_conditions":"selftest",
      "event_risk":"selftest","flip_conditions":"selftest","evidence_summary":"selftest"
    }

def base_quote():
    return {"source_id":"JPX_OSE_OFFICIAL","provider":"Japan Exchange Group / Osaka Exchange",
      "source_quality":"A","symbol":"NK225MCU2026","product":"Nikkei 225 micro Futures",
      "contract_month":"Sep.2026","contract_code":"115.2609/O","price":65000,
      "source_timestamp":"2026-09-07T08:05:00+08:00","freshness_age_seconds":300,
      "freshness_pass":True,"exact_product":True,"continuous_contract":False,
      "official_exchange_source":True}
def main():
    before=ledger_counts()
    if before!=(0,0): raise RuntimeError(f"real ledger must be 0/0 for pre-first-forecast selftest: {before}")
    results={}
    with tempfile.TemporaryDirectory(prefix="jnu_preflight_selftest_") as s:
        td=Path(s)
        req=base_request(); q=base_quote()
        code,out=run_case(td,"ready",req,q,"2026-09-07T08:10:00+08:00")
        results["ready"]={"pass":code==0 and out["status"]=="READY_FOR_ATOMIC_REGISTRATION","blockers":out["blockers"]}

        req=base_request()
        req["decision_input"]["risk_modifiers"]["event_state"]="UNKNOWN"
        req["risk_state_evidence"]["event_state"]="UNKNOWN"
        req["risk_state_evidence"]["event_sources"]=[]
        req["risk_state_evidence"]["event_unavailability_reason"]="synthetic calendar unavailable"
        code,out=run_case(td,"event_unknown",req,base_quote(),"2026-09-07T08:10:00+08:00")
        results["event_unknown"]={"pass":code==3 and "TARGET_HORIZON_EVENT_STATE_UNKNOWN" in out["blockers"],"blockers":out["blockers"]}

        req=base_request(); req.pop("risk_state_evidence")
        code,out=run_case(td,"missing_risk_evidence",req,base_quote(),"2026-09-07T08:10:00+08:00")
        results["missing_risk_evidence"]={"pass":code==3 and "RISK_STATE_EVIDENCE_MISSING" in out["blockers"],"blockers":out["blockers"]}
        req=base_request(); req["risk_state_evidence"]["event_state"]="PRE_RELEASE_HIGH"
        code,out=run_case(td,"risk_mismatch",req,base_quote(),"2026-09-07T08:10:00+08:00")
        results["risk_mismatch"]={"pass":code==3 and "RISK_STATE_EVIDENCE_MISMATCH_EVENT_STATE" in out["blockers"],"blockers":out["blockers"]}

        q=base_quote(); q["source_timestamp"]="2026-09-07T07:50:00+08:00"
        code,out=run_case(td,"stale_source",base_request(),q,"2026-09-07T08:10:00+08:00")
        results["stale_source"]={"pass":code==3 and "INDIVIDUAL_EXACT_MICRO_REFERENCE_FRESHNESS" in out["blockers"],"blockers":out["blockers"]}

        q=base_quote(); q["symbol"]="NK225MCZ2026"
        code,out=run_case(td,"symbol_mismatch",base_request(),q,"2026-09-07T08:10:00+08:00")
        results["symbol_mismatch"]={"pass":code==3 and "EXACT_MICRO_SYMBOL_MISMATCH" in out["blockers"],"blockers":out["blockers"]}

        code,out=run_case(td,"expired_request",base_request(),base_quote(),"2026-09-07T08:30:00+08:00")
        results["expired_request"]={"pass":code==3 and "REQUEST_EXPIRED_OR_NOT_YET_VALID" in out["blockers"],"blockers":out["blockers"]}

    after=ledger_counts()
    results["real_ledger_untouched"]={"pass":after==before== (0,0),"before":before,"after":after}
    status="PASS" if all(x["pass"] for x in results.values()) else "FAIL"
    print(json.dumps({"status":status,"tests":results},ensure_ascii=False,indent=2))
    raise SystemExit(0 if status=="PASS" else 1)

if __name__=="__main__":
    main()
