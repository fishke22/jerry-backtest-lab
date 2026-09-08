from __future__ import annotations
import argparse,json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from jnu_integrity_hash_v1 import canonical_text_sha256
from jnu_private_atomic_io_v1 import require_external,verify_backup,write_immutable_json
from validate_jnu_entitled_exact_micro_evidence_v1 import validate as validate_entitled_quote
ROOT=Path(__file__).resolve().parents[1];JST=timezone(timedelta(hours=9));CONTRACT=ROOT/"config"/"jnu_exact_micro_entitled_source_adapter_contract_v1.json";ROLL=ROOT/"config"/"jnu_exact_micro_contract_roll_calendar_v1.json"
def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict):raise RuntimeError(f"{p} must contain an object")
    return x
def dt(s:str)->datetime:
    x=datetime.fromisoformat(str(s))
    if x.tzinfo is None:raise RuntimeError("timestamp must be offset-aware")
    return x
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--private-ledger-root",type=Path,required=True);ap.add_argument("--forecast-id",required=True);ap.add_argument("--private-close-evidence",type=Path,required=True);a=ap.parse_args()
    require_external(a.private_ledger_root,"private ledger root");require_external(a.private_close_evidence,"private close evidence")
    fp=a.private_ledger_root.resolve()/"forecasts"/f"{a.forecast_id}.json"
    if not fp.exists():raise RuntimeError("private forecast not found")
    if verify_backup(a.private_ledger_root,fp).get("status")!="PASS":raise RuntimeError("private forecast backup integrity invalid")
    f=load(fp);e=load(a.private_close_evidence);close_sha=canonical_text_sha256(a.private_close_evidence)
    out=a.private_ledger_root.resolve()/"outcomes"/f"{a.forecast_id}.json"
    if out.exists():
        if verify_backup(a.private_ledger_root,out).get("status")!="PASS":raise RuntimeError("existing private outcome backup integrity invalid")
        old=load(out)
        if old.get("forecast_record_sha256")!=canonical_text_sha256(fp) or old.get("close_evidence_sha256")!=close_sha:raise RuntimeError("PRIVATE_OUTCOME_IDEMPOTENCY_CONFLICT")
        print(json.dumps({"status":"PRIVATE_ENTITLED_OUTCOME_ALREADY_RECORDED","forecast_id":a.forecast_id,"raw_and_derived_fields_not_printed":True,"public_output_created":False,"real_public_ledger_modified":False},indent=2));return
    qv=validate_entitled_quote(e,load(CONTRACT),load(ROLL))
    if str(e["canonical_symbol"]).upper()!=str(f["symbol"]).upper():raise RuntimeError("private close symbol mismatch")
    close_ts=dt(e["provider_timestamp"]);created=dt(f["created_at_taipei"])
    if close_ts<=created:raise RuntimeError("private outcome timestamp must be after forecast creation")
    if close_ts.astimezone(JST).date().isoformat()!=str(f["target_day_session_date"]):raise RuntimeError("private outcome target date mismatch")
    ref=float(f["reference_price"]);close=float(e["price"]);ret=close/ref-1.0;bias=f["bias"]
    if bias=="BULLISH":signed=ret;hit=True if ret>0 else (False if ret<0 else None)
    elif bias=="BEARISH":signed=-ret;hit=True if ret<0 else (False if ret>0 else None)
    else:signed=None;hit=None
    rec={"version":"1.1","artifact_class":"JNU_PRIVATE_ENTITLED_OUTCOME","forecast_id":a.forecast_id,"storage_scope":"PRIVATE_INTERNAL_ONLY","public_distribution_permitted":False,"forecast_record_sha256":canonical_text_sha256(fp),"forecast_record_sha256_method":"SHA256_TEXT_EOL_CRLF_V1","close_evidence_sha256":close_sha,"symbol":f["symbol"],"target_day_session_date":f["target_day_session_date"],"target_close_price":close,"target_close_timestamp":close_ts.isoformat(),"entitled_close_evidence":e,"entitled_close_validation":qv,"exact_product":True,"outcome_return":ret,"signed_outcome_return":signed,"directional_hit":hit,"immutable_record":True,"public_output_created":False}
    write_immutable_json(a.private_ledger_root,out,rec)
    print(json.dumps({"status":"PRIVATE_ENTITLED_OUTCOME_RECORDED","forecast_id":a.forecast_id,"raw_and_derived_fields_not_printed":True,"public_output_created":False,"real_public_ledger_modified":False},indent=2))
if __name__=="__main__":main()
