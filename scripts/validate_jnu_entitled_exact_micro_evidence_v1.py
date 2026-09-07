from __future__ import annotations
import argparse, json, re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"config"/"jnu_exact_micro_entitled_source_adapter_contract_v1.json"
ROLL=ROOT/"config"/"jnu_exact_micro_contract_roll_calendar_v1.json"
SYMBOL_RE=re.compile(r"^NK225MC[A-Z][0-9]{4}$")
SECRET_KEY_RE=re.compile(r"(password|passwd|api[_-]?key|secret|access[_-]?token|refresh[_-]?token|authorization|credential|x[_-]?api[_-]?key)",re.I)

def aware_dt(v:str,field:str)->datetime:
    x=datetime.fromisoformat(v)
    if x.tzinfo is None: raise RuntimeError(f"{field} must be offset-aware")
    return x

def scan_secret_keys(obj:Any,path:str="$")->list[str]:
    hits=[]
    if isinstance(obj,dict):
        for k,v in obj.items():
            p=f"{path}.{k}"
            if SECRET_KEY_RE.search(str(k)): hits.append(p)
            hits.extend(scan_secret_keys(v,p))
    elif isinstance(obj,list):
        for i,v in enumerate(obj): hits.extend(scan_secret_keys(v,f"{path}[{i}]"))
    return hits

def reqbool(e:dict,k:str,val:bool)->None:
    if e.get(k) is not val: raise RuntimeError(f"{k} must be {str(val).lower()}")

def validate(e:dict,contract:dict,roll:dict)->dict:
    hits=scan_secret_keys(e)
    if hits: raise RuntimeError("secret-like fields prohibited in evidence artifact: "+",".join(hits))
    missing=[k for k in contract["required_fields"] if k not in e]
    if missing: raise RuntimeError("missing required fields: "+",".join(missing))
    mode=e["entitlement_mode"]
    if mode not in contract["currently_allowed_entitlement_modes"]: raise RuntimeError(f"entitlement_mode not allowed by current governance: {mode}")
    if e["exchange"]!="OSE": raise RuntimeError("exchange must be OSE")
    if e["product"]!="Nikkei 225 micro Futures": raise RuntimeError("product identity mismatch")
    for k,val in [("exact_product",True),("continuous_contract",False),("broker_login_used",False),("trading_permission_used",False),("order_capable_session_used",False)]: reqbool(e,k,val)
    symbol=str(e["canonical_symbol"]).upper()
    if not SYMBOL_RE.fullmatch(symbol): raise RuntimeError("canonical_symbol must be exact individual NK225MC month symbol")
    entries={x["symbol"]:x for x in roll["entries"]}
    if symbol not in entries: raise RuntimeError("canonical_symbol not present in frozen roll calendar")
    if e["contract_month"]!=entries[symbol]["contract_month"]: raise RuntimeError("contract_month does not match frozen roll calendar")
    ident=e["identity_evidence"]
    if ident.get("exchange")!="OSE" or ident.get("product")!="Nikkei 225 micro Futures" or ident.get("contract_month")!=e["contract_month"] or not str(ident.get("provider_symbol","")).strip(): raise RuntimeError("identity_evidence mismatch")
    price=float(e["price"]); tick=float(e["tick_size"])
    if price<=0: raise RuntimeError("price must be positive")
    if tick!=5.0: raise RuntimeError("tick_size must equal frozen OSE Micro tick size 5")
    if abs(price/tick-round(price/tick))>1e-9: raise RuntimeError("price must align to 5-point tick")
    provider=aware_dt(str(e["provider_timestamp"]),"provider_timestamp")
    observed=aware_dt(str(e["observed_at_taipei"]),"observed_at_taipei")
    age=(observed-provider).total_seconds(); maxage=int(contract["maximum_reference_age_seconds"])
    if age<0: raise RuntimeError(f"provider timestamp is in the future: age={age:.3f}")
    if age>maxage: raise RuntimeError(f"quote stale: age={age:.3f}s > {maxage}s")
    if not str(e["provider_name"]).strip() or not str(e["entitlement_reference"]).strip() or not str(e["transport_qualification_id"]).strip(): raise RuntimeError("provider/entitlement/qualification reference required")
    reqbool(e,"positive_margin_demonstrated",True)
    if e["storage_scope"]!="PRIVATE_INTERNAL_ONLY": raise RuntimeError("storage_scope must be PRIVATE_INTERNAL_ONLY")
    if e["evidence_destination_class"]!="PRIVATE_INTERNAL_STORE": raise RuntimeError("evidence_destination_class must be PRIVATE_INTERNAL_STORE")
    reqbool(e,"raw_public_distribution_permitted",False)
    if e["third_party_cloud_processing_used"] is True and e["third_party_cloud_permission_status"]!="EXPLICITLY_APPROVED":
        raise RuntimeError("third-party cloud processing requires explicit approval")
    if e["public_derived_permission_status"] not in {"UNCONFIRMED","EXPLICITLY_APPROVED","PROHIBITED"}:
        raise RuntimeError("invalid public_derived_permission_status")
    return {"version":"1.0","status":"PASS","canonical_symbol":symbol,"contract_month":e["contract_month"],"entitlement_mode":mode,"provider_name":e["provider_name"],"freshness_age_seconds":round(age,6),"freshness_margin_seconds":round(maxage-age,6),"maximum_reference_age_seconds":maxage,"exact_product":True,"continuous_contract":False,"broker_login_used":False,"trading_permission_used":False,"order_capable_session_used":False,"secret_like_fields_present":False,"storage_scope":"PRIVATE_INTERNAL_ONLY","raw_public_distribution_permitted":False,"real_forecast_created":False,"real_ledger_modified":False}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--evidence",type=Path,required=True); ap.add_argument("--output",type=Path); a=ap.parse_args()
    e=json.loads(a.evidence.read_text(encoding="utf-8")); c=json.loads(CONTRACT.read_text(encoding="utf-8")); r=json.loads(ROLL.read_text(encoding="utf-8"))
    out=validate(e,c,r); s=json.dumps(out,ensure_ascii=False,indent=2)
    if a.output: a.output.write_text(s+"\n",encoding="utf-8")
    print(s)
if __name__=="__main__": main()
