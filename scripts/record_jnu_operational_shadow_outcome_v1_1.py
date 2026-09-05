from __future__ import annotations
import argparse, json
from datetime import datetime
from pathlib import Path
from jnu_integrity_hash_v1 import METHOD_ID, canonical_text_sha256

ROOT=Path(__file__).resolve().parents[1]
HASH_PROTOCOL=ROOT/"config"/"jnu_integrity_hash_protocol_v1.json"
DEFAULT_FORECAST=ROOT/"live_shadow"/"forecasts"
DEFAULT_OUTCOME=ROOT/"live_shadow"/"outcomes"

def sha(p:Path)->str: return canonical_text_sha256(p)
def dt(s:str)->datetime:
    x=datetime.fromisoformat(s)
    if x.tzinfo is None: raise RuntimeError("timestamp must be offset-aware")
    return x

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--forecast-id",required=True)
    ap.add_argument("--target-close-price",type=float,required=True)
    ap.add_argument("--target-close-timestamp",required=True)
    ap.add_argument("--target-close-source",required=True)
    ap.add_argument("--exact-product",action="store_true")
    ap.add_argument("--forecast-dir",type=Path,default=DEFAULT_FORECAST)
    ap.add_argument("--outcome-dir",type=Path,default=DEFAULT_OUTCOME)
    args=ap.parse_args()
    fp=args.forecast_dir/f"{args.forecast_id}.json"
    if not fp.exists(): raise RuntimeError("forecast record not found")
    f=json.loads(fp.read_text(encoding="utf-8"))
    if f.get("integrity_hash_method")!=METHOD_ID:
        raise RuntimeError("forecast integrity hash method mismatch")
    if f.get("integrity_hash_protocol_sha256")!=sha(HASH_PROTOCOL):
        raise RuntimeError("forecast integrity hash protocol SHA mismatch")
    if not args.exact_product: raise RuntimeError("exact-product flag required")
    if args.target_close_price<=0: raise RuntimeError("target close must be positive")
    td=dt(args.target_close_timestamp)
    created=dt(f["created_at_taipei"])
    if td<=created: raise RuntimeError("outcome timestamp must be after forecast creation")
    if td.date().isoformat()!=f["target_day_session_date"]: raise RuntimeError("outcome date does not match frozen target_day_session_date")
    ret=args.target_close_price/float(f["reference_price"])-1.0
    bias=f["bias"]
    if bias=="BULLISH": signed=ret; hit=True if ret>0 else (False if ret<0 else None)
    elif bias=="BEARISH": signed=-ret; hit=True if ret<0 else (False if ret>0 else None)
    else: signed=None; hit=None
    out={
      "version":"1.1","forecast_id":args.forecast_id,
      "forecast_record_sha256":sha(fp),
      "forecast_record_sha256_method":METHOD_ID,
      "integrity_hash_protocol_sha256":sha(HASH_PROTOCOL),
      "target_close_price":args.target_close_price,
      "target_close_timestamp":args.target_close_timestamp,
      "target_close_source":args.target_close_source,
      "exact_product":True,
      "outcome_return":ret,
      "directional_hit":hit,
      "signed_outcome_return":signed
    }
    args.outcome_dir.mkdir(parents=True,exist_ok=True)
    op=args.outcome_dir/f"{args.forecast_id}.json"
    if op.exists(): raise RuntimeError("outcome already exists")
    op.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"OUTCOME_RECORDED_V1_1","forecast_id":args.forecast_id,"outcome_return":ret,"directional_hit":hit,"path":str(op),"record_sha256":sha(op)},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
