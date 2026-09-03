from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FRAMEWORK=ROOT/"config"/"jnu_operational_framework_current_v1_1.json"
PREREG=ROOT/"config"/"jnu_operational_live_shadow_prereg_v1.json"
IMPL=ROOT/"config"/"jnu_operational_live_shadow_implementation_v1.json"
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
    required=json.loads(IMPL.read_text(encoding="utf-8"))["forecast_record"]["required_fields"]
    missing=[k for k in required if k not in x]
    if missing: raise RuntimeError(f"missing required fields: {missing}")
    created=parse_dt(str(x["created_at_taipei"]))
    ref=parse_dt(str(x["reference_timestamp"]))
    if created.utcoffset()!=timedelta(hours=8): raise RuntimeError("created_at_taipei must have +08:00 offset")
    if ref>created: raise RuntimeError("reference timestamp is after forecast creation")
    age=(created-ref).total_seconds()/60
    if age<0 or age>15: raise RuntimeError(f"reference age {age:.2f} minutes exceeds 15")
    if x.get("exact_product") is not True: raise RuntimeError("exact_product must be true")
    price=float(x["reference_price"])
    if not (price>0): raise RuntimeError("reference_price must be positive")
    if x["bias"] not in {"BULLISH","BEARISH","NEUTRAL_ABSTAIN"}: raise RuntimeError("invalid bias")
    if x["confidence"] not in {"LOW","MEDIUM"}: raise RuntimeError("invalid confidence")
    datetime.fromisoformat(str(x["target_day_session_date"]))
    for k in ["reference_source","expected_path","invalidation_conditions","event_risk","flip_conditions","evidence_summary"]:
        if not str(x[k]).strip(): raise RuntimeError(f"{k} must be nonempty")
    base={
      **x,
      "framework_sha256":sha(FRAMEWORK),
      "shadow_prereg_sha256":sha(PREREG),
      "implementation_sha256":sha(IMPL),
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
    print(json.dumps({"status":"FORECAST_REGISTERED_IMMUTABLE","forecast_id":fid,"path":str(out),"record_sha256":sha(out)},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
