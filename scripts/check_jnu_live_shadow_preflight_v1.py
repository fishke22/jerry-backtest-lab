from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from jnu_exact_micro_source_validation_v1 import validate_reference_source_metadata
from jnu_risk_state_evidence_validation_v1 import validate_risk_state_evidence
from jnu_integrity_hash_v1 import METHOD_ID, canonical_text_sha256

ROOT=Path(__file__).resolve().parents[1]
TAIPEI=timezone(timedelta(hours=8))
PROTOCOL=ROOT/"config"/"jnu_operational_decision_protocol_v1.json"
FRAMEWORK=ROOT/"config"/"jnu_operational_framework_current_v1_6.json"
PREREG=ROOT/"config"/"jnu_operational_live_shadow_prereg_v1_5.json"
IMPL=ROOT/"config"/"jnu_operational_live_shadow_implementation_v1_5.json"
DECISION=ROOT/"scripts"/"apply_jnu_operational_decision_protocol_v1.py"
REQUEST_PROTOCOL=ROOT/"config"/"jnu_cloud_forecast_request_protocol_v1_1.json"
HASH_PROTOCOL=ROOT/"config"/"jnu_integrity_hash_protocol_v1.json"
REAL_FD=ROOT/"live_shadow"/"forecasts"
REAL_OD=ROOT/"live_shadow"/"outcomes"

def sha(p:Path)->str:
    return canonical_text_sha256(p)

def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise RuntimeError(f"{p} must contain an object")
    return x

def dt(s:str)->datetime:
    x=datetime.fromisoformat(s)
    if x.tzinfo is None: raise RuntimeError("timestamp must be offset-aware")
    return x
def run_decision(decision_input:dict)->dict:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="jnu_preflight_") as td:
        inp=Path(td)/"decision.json"; out=Path(td)/"trace.json"
        inp.write_text(json.dumps(decision_input,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        subprocess.run([sys.executable,str(DECISION),"--input",str(inp),"--output",str(out)],
                       cwd=ROOT,check=True,capture_output=True,text=True)
        return load(out)

def real_ledger_counts()->tuple[int,int]:
    f=len(list(REAL_FD.glob("*.json"))) if REAL_FD.exists() else 0
    o=len(list(REAL_OD.glob("*.json"))) if REAL_OD.exists() else 0
    return f,o

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--request",type=Path,required=True)
    ap.add_argument("--quote",type=Path,required=True)
    ap.add_argument("--now-taipei")
    ap.add_argument("--output",type=Path)
    ap.add_argument("--require-empty-real-ledger",action="store_true")
    ap.add_argument("--require-risk-evidence",action="store_true")
    args=ap.parse_args()

    req=load(args.request); q=load(args.quote)
    now=dt(args.now_taipei).astimezone(TAIPEI) if args.now_taipei else datetime.now(TAIPEI)
    blockers=[]; checks={}
    created=dt(str(req["request_created_at_taipei"])).astimezone(TAIPEI)
    until=dt(str(req["request_valid_until_taipei"])).astimezone(TAIPEI)
    checks["request_window_seconds"]=(until-created).total_seconds()
    if not (created<=now<=until): blockers.append("REQUEST_EXPIRED_OR_NOT_YET_VALID")
    request_symbol=str(req.get("symbol","")).upper()
    if str(q.get("symbol","")).upper()!=request_symbol:
        blockers.append("EXACT_MICRO_SYMBOL_MISMATCH")
    try:
        source_class=validate_reference_source_metadata(
            q,float(q["price"]),str(q["source_timestamp"])
        )
        source_ts=dt(str(q["source_timestamp"])).astimezone(TAIPEI)
        source_age=(now-source_ts).total_seconds()
        checks["source_class"]=source_class
        checks["source_age_seconds"]=source_age
        if source_age<0 or source_age>900:
            blockers.append("INDIVIDUAL_EXACT_MICRO_REFERENCE_FRESHNESS")
    except Exception as e:
        source_class=None
        checks["source_validation_error"]=str(e)
        blockers.append("EXACT_MICRO_SOURCE_VALIDATION")

    decision_input=req.get("decision_input")
    if not isinstance(decision_input,dict):
        blockers.append("DECISION_INPUT_MISSING")
        trace=None
    else:
        trace=run_decision(decision_input)
        risk=trace.get("risk_modifiers") or {}
        checks["risk_modifiers"]=risk
        if risk.get("event_state")=="UNKNOWN":
            blockers.append("TARGET_HORIZON_EVENT_STATE_UNKNOWN")

    evidence=req.get("risk_state_evidence")
    if args.require_risk_evidence:
        if not isinstance(evidence,dict):
            blockers.append("RISK_STATE_EVIDENCE_MISSING")
        else:
            try:
                checks["risk_state_evidence"]=validate_risk_state_evidence(
                    evidence,trace,str(now.isoformat()),
                    request_created_at=str(req["request_created_at_taipei"]),
                    target_day_session_date=str(req["target_day_session_date"]),
                )
            except Exception as e:
                msg=str(e)
                checks["risk_evidence_error"]=msg
                if msg.startswith("risk evidence mismatch: "):
                    key=msg.split(": ",1)[1].upper()
                    blockers.append(f"RISK_STATE_EVIDENCE_MISMATCH_{key}")
                elif "event source" in msg:
                    blockers.append("EVENT_EVIDENCE_SOURCE_INVALID")
                else:
                    blockers.append("RISK_STATE_EVIDENCE_INVALID")

    fcount,ocount=real_ledger_counts()
    checks["real_ledger"]={"forecasts":fcount,"outcomes":ocount}
    if args.require_empty_real_ledger and (fcount!=0 or ocount!=0):
        blockers.append("REAL_LEDGER_NOT_EMPTY")
    checks["hash_chain"]={
        "framework_sha256":sha(FRAMEWORK),
        "prereg_sha256":sha(PREREG),
        "implementation_sha256":sha(IMPL),
        "protocol_sha256":sha(PROTOCOL),
        "request_protocol_sha256":sha(REQUEST_PROTOCOL),
        "integrity_hash_method":METHOD_ID,
        "integrity_hash_protocol_sha256":sha(HASH_PROTOCOL),
    }
    result={
        "version":"1.0",
        "status":"READY_FOR_ATOMIC_REGISTRATION" if not blockers else "BLOCKED_FAIL_CLOSED",
        "checked_at_taipei":now.isoformat(),
        "blockers":sorted(set(blockers)),
        "checks":checks,
        "decision_trace":trace,
        "source_class":source_class,
        "real_registration_performed":False,
    }
    s=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(s+"\n",encoding="utf-8")
    print(s)
    raise SystemExit(0 if not blockers else 3)

if __name__=="__main__":
    main()
