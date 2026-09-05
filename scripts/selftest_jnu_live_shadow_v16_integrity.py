from __future__ import annotations
import json, shutil, subprocess, sys, tempfile
from pathlib import Path
from jnu_integrity_hash_v1 import METHOD_ID, canonical_text_sha256

ROOT=Path(__file__).resolve().parents[1]
PY=sys.executable
PREFLIGHT=ROOT/"scripts"/"check_jnu_live_shadow_preflight_v1.py"
BUILDER=ROOT/"scripts"/"build_jnu_cloud_forecast_input_v1.py"
ATOMIC=ROOT/"scripts"/"register_jnu_operational_shadow_forecast_atomic_v2.py"
OUTCOME=ROOT/"scripts"/"record_jnu_operational_shadow_outcome_atomic_v2.py"
SCORER=ROOT/"scripts"/"score_jnu_operational_live_shadow_v1_4.py"
REAL_FD=ROOT/"live_shadow"/"forecasts"
REAL_OD=ROOT/"live_shadow"/"outcomes"

def run(cmd,check=True):
    return subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,check=check)

def counts():
    return (
        len(list(REAL_FD.glob("*.json"))) if REAL_FD.exists() else 0,
        len(list(REAL_OD.glob("*.json"))) if REAL_OD.exists() else 0,
    )

def write_json(path:Path,x:dict):
    path.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def request_fixture():
    return {
      "request_id":"JNU_REQ_V16_INTEGRITY_SELFTEST",
      "request_created_at_taipei":"2026-09-07T08:10:00+08:00",
      "request_valid_until_taipei":"2026-09-07T08:25:00+08:00",
      "symbol":"NK225MCU2026","target_day_session_date":"2026-09-07",
      "decision_input":{
        "blocks":[
          {"id":"EXACT_JNU_PRICE_PATH","vote":"BEARISH","quality":"A","reason":"synthetic path"},
          {"id":"DYNAMIC_PRICE_DISCOVERY","vote":"NEUTRAL","quality":"B","reason":"synthetic neutral"},
          {"id":"CONTEMPORANEOUS_CROSS_MARKET","vote":"BEARISH","quality":"B","reason":"synthetic cross"},
          {"id":"POSITIONING_DERIVATIVES_CONTEXT","vote":"NEUTRAL","quality":"B","reason":"synthetic neutral"}
        ],
        "risk_modifiers":{"volatility_state":"UNKNOWN","event_state":"NORMAL","sq_state":"UNKNOWN",
                          "post_event_exact_jnu_path_available":False}
      },
      "risk_state_evidence":{
        "checked_at_taipei":"2026-09-07T08:09:00+08:00",
        "target_day_session_date":"2026-09-07",
        "event_state":"NORMAL","volatility_state":"UNKNOWN","sq_state":"UNKNOWN",
        "event_sources":[{"source":"synthetic official calendar","reference":"selftest",
                          "checked_at_taipei":"2026-09-07T08:09:00+08:00"}]
      },
      "expected_path":"synthetic","key_levels":[65000],
      "invalidation_conditions":"synthetic","event_risk":"synthetic",
      "flip_conditions":"synthetic","evidence_summary":"synthetic"
    }

def quote_fixture():
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
        raise RuntimeError(f"pre-first-forecast integrity selftest requires real ledger 0/0, got {before}")
    tests={}
    with tempfile.TemporaryDirectory(prefix="jnu_v16_integrity_") as td0:
        td=Path(td0); fd=td/"forecasts"; od=td/"outcomes"
        req=td/"request.json"; quote=td/"quote.json"; atomic=td/"atomic.json"
        write_json(req,request_fixture()); write_json(quote,quote_fixture())

        cp=run([PY,str(PREFLIGHT),"--request",str(req),"--quote",str(quote),
                "--now-taipei","2026-09-07T08:10:00+08:00",
                "--require-empty-real-ledger","--require-risk-evidence",
                "--output",str(td/"preflight.json")],check=False)
        tests["preflight_ready"]=cp.returncode==0

        run([PY,str(BUILDER),"--request",str(req),"--quote",str(quote),
             "--created-at-taipei","2026-09-07T08:10:00+08:00","--output",str(atomic)])
        cp=run([PY,str(ATOMIC),"--input",str(atomic),"--output-dir",str(fd)])
        reg=json.loads(cp.stdout); fid=reg["forecast_id"]
        f=json.loads((fd/f"{fid}.json").read_text(encoding="utf-8"))
        tests["atomic_v2_risk_bound"]=bool(
            f["risk_state_evidence_validation"]["event_state"]=="NORMAL"
            and f["integrity_hash_method"]==METHOD_ID
            and f["framework_sha256"] and f["shadow_prereg_sha256"] and f["implementation_sha256"]
        )
        original=(fd/f"{fid}.json").read_bytes()
        logical=original.replace(b"\r\n",b"\n").replace(b"\r",b"\n")
        lf=td/"forecast_lf.json"; crlf=td/"forecast_crlf.json"
        lf.write_bytes(logical)
        crlf.write_bytes(logical.replace(b"\n",b"\r\n"))
        tests["cross_platform_eol_hash_equal"]=(
            canonical_text_sha256(lf)==canonical_text_sha256(crlf)==canonical_text_sha256(fd/f"{fid}.json")
        )
        run([PY,str(OUTCOME),"--forecast-id",fid,"--target-close-price","64000",
             "--target-close-timestamp","2026-09-07T15:45:00+09:00",
             "--target-close-source","synthetic exact Micro close","--exact-product",
             "--forecast-dir",str(fd),"--outcome-dir",str(od)])
        forecast_path=fd/f"{fid}.json"
        forecast_logical=forecast_path.read_bytes().replace(b"\r\n",b"\n").replace(b"\r",b"\n")
        forecast_path.write_bytes(forecast_logical)
        tests["outcome_survives_forecast_eol_conversion"]=(
            b"\r\n" not in forecast_path.read_bytes()
        )
        cp=run([PY,str(SCORER),"--forecast-dir",str(fd),"--outcome-dir",str(od),
                "--output",str(td/"score.json"),"--selftest-untracked"])
        score=json.loads((td/"score.json").read_text(encoding="utf-8"))
        tests["scorer_v14_chain"]=(
            score["integrity"]["status"]=="PASS"
            and score["integrity"]["forecasts_verified"]==1
            and score["integrity"]["outcomes_verified"]==1
        )

        tamper=td/"tamper_forecasts"; shutil.copytree(fd,tamper)
        tp=tamper/f"{fid}.json"; tx=json.loads(tp.read_text(encoding="utf-8"))
        tx["risk_state_evidence"]["event_state"]="PRE_RELEASE_HIGH"
        write_json(tp,tx)
        cp=run([PY,str(SCORER),"--forecast-dir",str(tamper),"--outcome-dir",str(od),
                "--output",str(td/"tamper_score.json"),"--selftest-untracked"],check=False)
        tests["risk_evidence_tamper_rejected"]=(cp.returncode!=0 and "risk evidence mismatch" in cp.stderr)

        missing=json.loads(atomic.read_text(encoding="utf-8")); missing.pop("risk_state_evidence")
        mp=td/"missing_risk.json"; write_json(mp,missing)
        cp=run([PY,str(ATOMIC),"--input",str(mp),"--output-dir",str(td/"missing_out")],check=False)
        tests["atomic_missing_risk_rejected"]=(cp.returncode!=0 and "risk_state_evidence" in cp.stderr)

        bad_window=json.loads(atomic.read_text(encoding="utf-8"))
        bad_window["request_valid_until_taipei"]="2026-09-07T08:09:00+08:00"
        wp=td/"bad_window.json"; write_json(wp,bad_window)
        cp=run([PY,str(ATOMIC),"--input",str(wp),"--output-dir",str(td/"bad_window_out")],check=False)
        tests["atomic_request_window_rejected"]=(
            cp.returncode!=0 and ("request validity window" in cp.stderr or "outside immutable request" in cp.stderr)
        )

        bad_symbol=json.loads(atomic.read_text(encoding="utf-8"))
        bad_symbol["symbol"]="NK225MCZ2026"
        sp=td/"bad_symbol.json"; write_json(sp,bad_symbol)
        cp=run([PY,str(ATOMIC),"--input",str(sp),"--output-dir",str(td/"bad_symbol_out")],check=False)
        tests["atomic_symbol_source_mismatch_rejected"]=(
            cp.returncode!=0 and "symbol does not match source metadata symbol" in cp.stderr
        )

    after=counts()
    tests["real_ledger_untouched"]=(before==after==(0,0))
    status="PASS" if all(tests.values()) else "FAIL"
    print(json.dumps({"status":status,"tests":tests,"real_ledger_before":before,"real_ledger_after":after},
                     ensure_ascii=False,indent=2))
    raise SystemExit(0 if status=="PASS" else 1)

if __name__=="__main__":
    main()
