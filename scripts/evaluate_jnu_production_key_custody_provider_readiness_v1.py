from __future__ import annotations
import argparse,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MATRIX=ROOT/"config"/"jnu_production_key_custody_decision_matrix_v1.json"
TERMS_PROTOCOL=ROOT/"config"/"jnu_provider_term_readiness_protocol_v1.json"

def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict):raise RuntimeError(f"{p} must contain an object")
    return x

def evaluate_key(profile:dict,matrix:dict)->dict:
    blockers=[]
    prohibited=set(matrix["prohibited_production_classes"])
    if profile.get("control_class") in prohibited:blockers.append("PROHIBITED_KEY_CUSTODY_CLASS")
    if profile.get("control_class") not in {matrix["preferred_control_class"],matrix["escalation_control_class"]}:
        blockers.append("PRODUCTION_KEY_CUSTODY_CLASS_NOT_SELECTED")
    req=matrix["hard_requirements"]
    for k,v in req.items():
        if k=="minimum_fips_security_level":
            if int(profile.get("fips_security_level",0))<int(v):blockers.append("FIPS_SECURITY_LEVEL_BELOW_MINIMUM")
        elif profile.get(k) is not v:
            blockers.append("KEY_CONTROL_"+k.upper()+"_NOT_SATISFIED")
    if profile.get("production_enabled") is not True:blockers.append("PRODUCTION_KEY_PROFILE_NOT_ENABLED")
    if str(profile.get("vendor","UNSELECTED"))=="UNSELECTED":blockers.append("KMS_HSM_VENDOR_UNSELECTED")
    if str(profile.get("region","UNSELECTED"))=="UNSELECTED":blockers.append("KMS_HSM_REGION_UNSELECTED")
    return {"status":"PASS" if not blockers else "BLOCKED","blockers":sorted(set(blockers))}

def evaluate_terms(x:dict,p:dict)->dict:
    missing=[k for k in p["required_fields"] if k not in x]
    if missing:return {"status":"BLOCKED","blockers":["MISSING_TERM_FIELDS:"+",".join(missing)]}
    blockers=[]
    for k,v in p["ready_values"].items():
        if x.get(k)!=v:blockers.append("TERM_"+k.upper()+"_NOT_READY")
    if x["service_facilitator_required"] is True:
        if x["service_facilitator_approval_status"]!="EXPLICITLY_APPROVED":
            blockers.append("SERVICE_FACILITATOR_APPROVAL_NOT_READY")
    else:
        if x["service_facilitator_approval_status"]!="NOT_REQUIRED":
            blockers.append("SERVICE_FACILITATOR_STATUS_INVALID")
    if x["broker_auth_used"] is not False:blockers.append("BROKER_AUTH_PROHIBITED")
    if x["trading_permission_used"] is not False:blockers.append("TRADING_PERMISSION_PROHIBITED")
    if x["public_output_requested"] is not False:blockers.append("PUBLIC_OUTPUT_NOT_AUTHORIZED_BY_THIS_GATE")
    return {"status":"PASS" if not blockers else "BLOCKED","blockers":sorted(set(blockers))}

def evaluate(key_profile:dict,terms:dict)->dict:
    km=load(MATRIX);tp=load(TERMS_PROTOCOL)
    k=evaluate_key(key_profile,km);t=evaluate_terms(terms,tp)
    blockers=sorted(set(k["blockers"]+t["blockers"]))
    return {
      "version":"1.0",
      "status":"READY_FOR_REAL_ENCRYPTED_BACKUP_PRIVATE_ONLY" if not blockers else "BLOCKED",
      "key_custody":k,
      "provider_terms":t,
      "blockers":blockers,
      "public_output_authorized":False,
      "real_entitled_backup_activation_permitted":not blockers
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--key-profile",type=Path,required=True)
    ap.add_argument("--provider-terms",type=Path,required=True)
    ap.add_argument("--output",type=Path)
    ap.add_argument("--report-only",action="store_true")
    a=ap.parse_args()
    out=evaluate(load(a.key_profile),load(a.provider_terms))
    s=json.dumps(out,ensure_ascii=False,indent=2)
    if a.output:a.output.write_text(s+"\n",encoding="utf-8")
    print(s)
    if out["status"]!="READY_FOR_REAL_ENCRYPTED_BACKUP_PRIVATE_ONLY" and not a.report_only:
        raise SystemExit(3)
if __name__=="__main__":main()
