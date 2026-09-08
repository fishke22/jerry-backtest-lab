from __future__ import annotations
import copy, json
from pathlib import Path
from validate_jnu_provider_evidence_intake_pack_v1 import load, validate, PROTOCOL, SHORTLIST, TEMPLATES

ROOT=Path(__file__).resolve().parents[1]
MEMORY=ROOT/"config"/"jnu_operational_framework_cross_session_memory_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"

p=load(PROTOCOL);s=load(SHORTLIST);t=load(TEMPLATES)
T={}

def rejected(mutator):
    x=copy.deepcopy(t); mutator(x)
    try:
        validate(p,s,x)
        return False
    except Exception:
        return True

r=validate(p,s,t)
T["baseline_pass"]=r["status"]=="PASS_DRAFT_PACK_READY_UNSENT"
T["covers_all_market_data_candidates"]=r["market_data_candidates_covered"]==3
T["covers_all_key_custody_candidates"]=r["key_custody_candidates_covered"]==2
T["ose_authority_pack_present"]=r["ose_authority_pack"] is True
T["outreach_remains_unsent"]=r["outreach_sent"] is False
T["provider_selection_not_performed"]=r["provider_selection_performed"] is False
T["real_activation_not_generated"]=r["real_activation_manifest_generated"] is False
T["missing_market_candidate_rejected"]=rejected(lambda x:x["market_data_provider_packs"].pop())
T["outreach_authorization_rejected"]=rejected(lambda x:x["market_data_provider_packs"][0].__setitem__("outreach_authorized",True))
T["secret_field_rejected"]=rejected(lambda x:x["market_data_provider_packs"][0].__setitem__("api_key","synthetic"))
T["missing_required_question_rejected"]=rejected(lambda x:x["market_data_provider_packs"][0].__setitem__("questionnaire",[q for q in x["market_data_provider_packs"][0]["questionnaire"] if q["target_field"]!="dr_drill_permission_status"]))
T["unknown_kms_candidate_rejected"]=rejected(lambda x:x["key_custody_deployment_packs"][0].__setitem__("candidate_id","UNKNOWN_KMS"))
T["premature_kms_attestation_rejected"]=rejected(lambda x:x["key_custody_deployment_packs"][0]["deployment_attestation"][0].update({"status":"APPROVED","attestation_value":"x","reviewer_attestation":"x"}))
mem=load(MEMORY);kc=load(KEY_CURRENT);terms=load(TERMS_CURRENT)
T["public_real_ledger_still_zero_zero"]=mem.get("real_live_shadow_forecasts_registered")==0 and mem.get("real_live_shadow_outcomes_registered")==0
T["production_key_still_disabled"]=kc.get("production_enabled") is False and kc.get("vendor")=="UNSELECTED"
T["provider_terms_still_unresolved"]=any(v=="UNRESOLVED" for k,v in terms.items() if k.endswith("_status"))
status="PASS" if all(T.values()) else "FAIL"
print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T)},indent=2))
raise SystemExit(0 if status=="PASS" else 1)
