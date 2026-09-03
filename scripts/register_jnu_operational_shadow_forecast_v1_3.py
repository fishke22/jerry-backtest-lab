from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FRAMEWORK=ROOT/"config"/"jnu_operational_framework_current_v1_4.json"
PREREG=ROOT/"config"/"jnu_operational_live_shadow_prereg_v1_3.json"
IMPL=ROOT/"config"/"jnu_operational_live_shadow_implementation_v1_3.json"
PROTOCOL=ROOT/"config"/"jnu_operational_decision_protocol_v1.json"
DEFAULT_DIR=ROOT/"live_shadow"/"forecasts"

def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def parse_dt(s:str)->datetime:
    d=datetime.fromisoformat(s)
    if d.tzinfo is None: raise ValueError("timestamp must be offset-aware")
    return d

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,required=True)
    ap.add_argument("--output-dir",type=Path,default=DEFAULT_DIR)
    args=ap.parse_args()
    x=json.loads(args.input.read_text(encoding="utf-8"))
    impl=json.loads(IMPL.read_text(encoding="utf-8"))
    required=impl.get("required_fields") or [
      "created_at_taipei","reference_price","reference_timestamp","reference_source","exact_product",
      "target_day_session_date","bias","confidence","decision_trace","expected_path","key_levels",
      "invalidation_conditions","event_risk","flip_conditions","evidence_summary"
    ]
    missing=[k for k in required if k not in x]
    if missing: raise RuntimeError(f"missing required fields: {missing}")
    created=parse_dt(str(x["created_at_taipei"])); ref=parse_dt(str(x["reference_timestamp"]))
    if created.utcoffset()!=timedelta(hours=8): raise RuntimeError("created_at_taipei must have +08:00 offset")
    if ref>created: raise RuntimeError("reference timestamp is after forecast creation")
    age=(created-ref).total_seconds()/60
    if age<0 or age>15: raise RuntimeError(f"reference age {age:.2f} minutes exceeds 15")
    if x.get("exact_product") is not True: raise RuntimeError("exact_product must be true")
    if float(x["reference_price"])<=0: raise RuntimeError("reference_price must be positive")
    if x["bias"] not in {"BULLISH","BEARISH","NEUTRAL_ABSTAIN"}: raise RuntimeError("invalid bias")
    if x["confidence"] not in {"LOW","MEDIUM"}: raise RuntimeError("invalid confidence")
    datetime.fromisoformat(str(x["target_day_session_date"]))
    for k in ["reference_source","expected_path","invalidation_conditions","event_risk","flip_conditions","evidence_summary"]:
        if not str(x[k]).strip(): raise RuntimeError(f"{k} must be nonempty")
    meta=x["reference_source_metadata"]
    if not isinstance(meta,dict): raise RuntimeError("reference_source_metadata must be an object")
    if meta.get("exact_product") is not True: raise RuntimeError("reference source metadata exact_product must be true")
    if meta.get("continuous_contract") is not False: raise RuntimeError("continuous contract is prohibited as primary scored reference")
    if meta.get("source_id")!="OSE": raise RuntimeError("reference source metadata source_id must be OSE")
    msym=str(meta.get("symbol",""))
    if not __import__("re").fullmatch(r"NK225MC[A-Z][0-9]{4}",msym): raise RuntimeError("reference source metadata must identify an individual OSE Micro contract")
    if abs(float(meta.get("price"))-float(x["reference_price"]))>1e-12: raise RuntimeError("reference source metadata price mismatch")
    if str(meta.get("source_timestamp"))!=str(x["reference_timestamp"]): raise RuntimeError("reference source metadata timestamp mismatch")
    if meta.get("freshness_pass") is not True: raise RuntimeError("reference source metadata freshness_pass must be true")
    mage=float(meta.get("freshness_age_seconds"))
    if mage<0 or mage>15*60: raise RuntimeError("reference source metadata age exceeds 900 seconds")
    trace=x["decision_trace"]
    if not isinstance(trace,dict): raise RuntimeError("decision_trace must be an object")
    protocol_sha=sha(PROTOCOL)
    if trace.get("protocol_sha256")!=protocol_sha: raise RuntimeError("decision_trace protocol SHA mismatch")
    if trace.get("bias")!=x["bias"]: raise RuntimeError("forecast bias does not match decision_trace bias")
    if trace.get("confidence")!=x["confidence"]: raise RuntimeError("forecast confidence does not match decision_trace confidence")
    if trace.get("calibrated_probability") is not False: raise RuntimeError("decision_trace calibrated_probability must be false")
    frozen_ids=[b["id"] for b in json.loads(PROTOCOL.read_text(encoding="utf-8"))["directional_blocks"]]
    blocks=trace.get("blocks")
    if not isinstance(blocks,list) or sorted(b.get("id") for b in blocks)!=sorted(frozen_ids):
        raise RuntimeError("decision_trace blocks do not exactly match frozen directional blocks")
    base={
      **x,
      "framework_sha256":sha(FRAMEWORK),
      "shadow_prereg_sha256":sha(PREREG),
      "implementation_sha256":sha(IMPL),
      "decision_protocol_sha256":protocol_sha,
      "registered_at_utc":datetime.now(timezone.utc).isoformat(),
      "immutable_record":True,
      "outcome_known_at_registration":False
    }
    canonical=json.dumps(base,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    token=hashlib.sha256(canonical).hexdigest()[:12]
    stamp=created.strftime("%Y%m%dT%H%M%S")
    fid=f"JNU_LS_{stamp}_{token}"
    base["forecast_id"]=fid
    args.output_dir.mkdir(parents=True,exist_ok=True)
    out=args.output_dir/f"{fid}.json"
    if out.exists(): raise RuntimeError(f"forecast already exists: {out}")
    out.write_text(json.dumps(base,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"FORECAST_REGISTERED_IMMUTABLE_V1_3","forecast_id":fid,"path":str(out),"record_sha256":sha(out)},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
