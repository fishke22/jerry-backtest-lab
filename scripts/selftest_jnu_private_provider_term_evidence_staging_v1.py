from __future__ import annotations
import copy, hashlib, json, tempfile
from pathlib import Path
from stage_jnu_private_provider_term_evidence_v1 import stage, load, validate_intake, ROOT
from emit_jnu_redacted_provider_term_attestation_v1 import emit

MEMORY=ROOT/"config"/"jnu_operational_framework_cross_session_memory_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"

def w(p:Path,x):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+"\n",encoding="utf-8")
def h(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def rejected(fn)->bool:
    try:fn();return False
    except Exception:return True

T={}
with tempfile.TemporaryDirectory(prefix="jnu-term-stage-") as td0:
    td=Path(td0)
    d1=td/"ose.txt";d2=td/"provider.txt"
    marker1="SYNTHETIC_CONFIDENTIAL_OSE_TEXT_DO_NOT_EMIT_42"
    marker2="SYNTHETIC_CONFIDENTIAL_PROVIDER_TEXT_DO_NOT_EMIT_77"
    d1.write_text(marker1+"\nsynthetic fixture only\n",encoding="utf-8")
    d2.write_text(marker2+"\nsynthetic fixture only\n",encoding="utf-8")
    base={
      "version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,
      "pack_id":"JNU_TERM_SYNTH_PIPE_001","evidence_as_of":"2026-09-08","subject_id":"OSE_AUTHORITY",
      "source":{
        "evidence_id":"E_SYNTH_OSE_001","source_class":"OSE_WRITTEN_CONFIRMATION","authority":"OSE",
        "source_uri":"urn:jnu:synthetic:ose:evidence:001","source_document_path":str(d1.resolve()),
        "document_sha256":h(d1),"captured_at_utc":"2026-09-08T00:00:00+00:00","confidentiality":"SYNTHETIC_PRIVATE"
      },
      "claims":[
        {"field":"entitlement_status","value":"EXPLICITLY_APPROVED","locator":"CLAUSE:1.1","explicitness":"EXPLICIT_TEXT","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"},
        {"field":"ose_third_party_cloud_processing_status","value":"EXPLICITLY_APPROVED","locator":"PAGE:2;CLAUSE:4","explicitness":"EXPLICIT_TEXT","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"}
      ]
    }
    p2=copy.deepcopy(base);p2["subject_id"]="BROadridge_CQG_OSE"
    p2["source"]={
      "evidence_id":"E_SYNTH_PROVIDER_001","source_class":"PROVIDER_WRITTEN_CONFIRMATION","authority":"MARKET_DATA_PROVIDER",
      "source_uri":"urn:jnu:synthetic:provider:evidence:001","source_document_path":str(d2.resolve()),
      "document_sha256":h(d2),"captured_at_utc":"2026-09-08T00:01:00+00:00","confidentiality":"SYNTHETIC_RESTRICTED"
    }
    p2["claims"]=[
      {"field":"read_only_transport_status","value":"EXPLICITLY_APPROVED","locator":"SECTION:READ_ONLY","explicitness":"EXPLICIT_TEXT","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"},
      {"field":"provider_third_party_cloud_processing_status","value":"EXPLICITLY_APPROVED","locator":"CLAUSE:CLOUD-2","explicitness":"EXPLICIT_TEXT","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"}
    ]
    m1=td/"m1.json";m2=td/"m2.json";s1=td/"s1.json";s2=td/"s2.json";out=td/"redacted.json";w(m1,base);w(m2,p2)
    r1=stage(m1,s1);r2=stage(m2,s2)
    T["stage_ose_pass"]=r1["source_document_sha256_verified"] is True
    T["stage_provider_pass"]=r2["source_document_sha256_verified"] is True
    er=emit([s1,s2],out);red=load(out);raw=out.read_text(encoding="utf-8")
    T["emit_partial_redacted_pass"]=er["attestation_status"]=="PARTIAL_EXPLICIT_TERMS_BLOCKED"
    T["redacted_has_no_source_path_key"]=all("source_document_path" not in row for row in red["evidence_ledger"].values() for row in row) and "source_document_path" not in red
    T["redacted_has_no_source_text_markers"]=marker1 not in raw and marker2 not in raw
    T["redacted_keeps_hash_locator_authority"]=red["evidence_ledger"]["entitlement_status"][0]["document_sha256"]==h(d1) and red["evidence_ledger"]["read_only_transport_status"][0]["locator"]=="SECTION:READ_ONLY" and red["evidence_ledger"]["read_only_transport_status"][0]["authority"]=="MARKET_DATA_PROVIDER"
    T["redacted_never_authorizes_real_activation"]=red["real_activation_authorized"] is False
    T["wrong_hash_rejected"]=rejected(lambda:validate_intake({**copy.deepcopy(base),"source":{**copy.deepcopy(base["source"]),"document_sha256":"0"*64}}))
    T["repo_internal_source_rejected"]=rejected(lambda:validate_intake({**copy.deepcopy(base),"source":{**copy.deepcopy(base["source"]),"source_document_path":str((ROOT/"README.md").resolve()),"document_sha256":h(ROOT/"README.md")}}))
    T["real_mode_rejected"]=rejected(lambda:validate_intake({**copy.deepcopy(base),"mode":"REAL","synthetic_fixture":False}))
    T["nonsynthetic_uri_rejected"]=rejected(lambda:validate_intake({**copy.deepcopy(base),"source":{**copy.deepcopy(base["source"]),"source_uri":"https://example.com/real-contract"}}))
    T["credential_like_uri_rejected"]=rejected(lambda:validate_intake({**copy.deepcopy(base),"source":{**copy.deepcopy(base["source"]),"source_uri":"urn:jnu:synthetic:ose:evidence:001?token=x"}}))
    T["secret_field_rejected"]=rejected(lambda:validate_intake({**copy.deepcopy(base),"api_key":"synthetic"}))
    T["invalid_source_class_rejected"]=rejected(lambda:validate_intake({**copy.deepcopy(base),"source":{**copy.deepcopy(base["source"]),"source_class":"UNKNOWN"}}))
    bad=copy.deepcopy(base);bad["source"]["authority"]="MARKET_DATA_PROVIDER"
    T["wrong_authority_for_ose_field_rejected"]=rejected(lambda:validate_intake(bad))
    bad=copy.deepcopy(base);bad["claims"][0]["locator"]="copied paragraph without locator prefix"
    T["free_text_locator_rejected"]=rejected(lambda:validate_intake(bad))
    bad=copy.deepcopy(base);bad["source"]["confidentiality"]="REAL_CONFIDENTIAL"
    T["real_confidentiality_class_rejected"]=rejected(lambda:validate_intake(bad))
    bad=copy.deepcopy(base);bad["claims"][0]["reviewer_attestation"]="INFERRED"
    T["inferred_reviewer_claim_rejected"]=rejected(lambda:validate_intake(bad))
    d1.write_text(marker1+"\ntampered after staging\n",encoding="utf-8")
    T["post_stage_source_tamper_rejected"]=rejected(lambda:emit([s1,s2],td/"tamper-out.json"))
    d1.write_text(marker1+"\nsynthetic fixture only\n",encoding="utf-8")
    conflict=copy.deepcopy(p2);conflict["source"]["evidence_id"]="E_SYNTH_PROVIDER_002";conflict["source"]["source_uri"]="urn:jnu:synthetic:provider:evidence:002"
    conflict["claims"]=[{"field":"exact_micro_product_status","value":"EXPLICITLY_CONFIRMED","locator":"CLAUSE:X","explicitness":"EXPLICIT_TEXT","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"}]
    c1=copy.deepcopy(base);c1["claims"]=[{"field":"exact_micro_product_status","value":"EXPLICITLY_APPROVED","locator":"CLAUSE:Y","explicitness":"EXPLICIT_TEXT","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"}]
    cm1=td/"cm1.json";cm2=td/"cm2.json";cs1=td/"cs1.json";cs2=td/"cs2.json";w(cm1,c1);w(cm2,conflict);stage(cm1,cs1);stage(cm2,cs2)
    T["cross_stage_conflict_rejected"]=rejected(lambda:emit([cs1,cs2],td/"conflict-out.json"))
    T["repo_internal_redacted_output_rejected"]=rejected(lambda:emit([s1,s2],ROOT/"should_not_exist.json"))

mem=load(MEMORY);kc=load(KEY_CURRENT);terms=load(TERMS_CURRENT)
T["public_real_ledger_still_zero_zero"]=mem.get("real_live_shadow_forecasts_registered")==0 and mem.get("real_live_shadow_outcomes_registered")==0
T["production_key_still_unselected_disabled"]=kc.get("production_enabled") is False and kc.get("vendor")=="UNSELECTED"
T["real_provider_terms_still_unresolved"]=any(v=="UNRESOLVED" for k,v in terms.items() if k.endswith("_status"))
status="PASS" if all(T.values()) else "FAIL"
print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T)},indent=2))
raise SystemExit(0 if status=="PASS" else 1)
