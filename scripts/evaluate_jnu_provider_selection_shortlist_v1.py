from __future__ import annotations
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"

def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict):raise RuntimeError(f"{p} must contain an object")
    return x

def evaluate(s:dict)->dict:
    if s.get("selected_market_data_provider")!="UNSELECTED" or s.get("selected_key_custody_provider")!="UNSELECTED":
        raise RuntimeError("shortlist file must not perform provider selection")
    md=[]
    for x in s["market_data_candidates"]:
        blockers=[]
        if x.get("ose_direct_market_information_provider_status")!="EVIDENCED":blockers.append("OSE_DIRECT_PROVIDER_NOT_EVIDENCED")
        if x.get("exact_nikkei_225_micro_individual_contract_status")!="EXPLICITLY_CONFIRMED":blockers.append("EXACT_MICRO_UNRESOLVED")
        if x.get("data_only_read_only_credential_status")!="EXPLICITLY_CONFIRMED":blockers.append("READ_ONLY_DATA_ONLY_CREDENTIAL_UNRESOLVED")
        if x.get("third_party_cloud_processing_permission")!="EXPLICITLY_APPROVED":blockers.append("CLOUD_PROCESSING_PERMISSION_UNRESOLVED")
        md.append({"id":x["id"],"status":"SELECTION_READY" if not blockers else "SHORTLIST_ONLY","blockers":blockers})
    kms=[]
    for x in s["key_custody_candidates"]:
        blockers=[]
        if x.get("control_class")!="MANAGED_HSM_BACKED_KMS":blockers.append("CONTROL_CLASS")
        if "LEVEL_3" not in str(x.get("hsm_fips_level_3_status","")):blockers.append("FIPS_LEVEL_3_NOT_EVIDENCED")
        for k in ["rotation_status","audit_logging_status"]:
            if x.get(k)!="EVIDENCED":blockers.append(k.upper()+"_UNRESOLVED")
        for k in ["private_network_path_status","iam_role_separation_status","deletion_protection_status"]:
            if x.get(k)!="EXPLICITLY_CONFIGURED":blockers.append(k.upper()+"_UNRESOLVED")
        kms.append({"id":x["id"],"status":"SELECTION_READY" if not blockers else "TECHNICAL_CANDIDATE_ONLY","blockers":blockers})
    return {"version":"1.0","status":"PASS_SHORTLIST_NO_SELECTION","market_data":md,"key_custody":kms,"real_provider_selection_performed":False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--shortlist",type=Path,default=SHORTLIST);a=ap.parse_args()
    print(json.dumps(evaluate(load(a.shortlist)),indent=2))
if __name__=="__main__":main()
