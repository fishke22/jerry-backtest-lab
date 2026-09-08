from __future__ import annotations
import copy,json
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("m",ROOT/"scripts"/"evaluate_jnu_production_key_custody_provider_readiness_v1.py");m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
matrix=json.loads((ROOT/"config"/"jnu_production_key_custody_decision_matrix_v1.json").read_text())
terms_protocol=json.loads((ROOT/"config"/"jnu_provider_term_readiness_protocol_v1.json").read_text())
K={"version":"1.0","status":"READY","control_class":"MANAGED_HSM_BACKED_KMS","vendor":"SYNTH_KMS","region":"SYNTH_REGION","hsm_backed":True,"fips_security_level":3,"kek_non_exportable":True,"symmetric_kek":True,"envelope_encryption":True,"per_backup_random_dek":True,"kek_wraps_dek_only":True,"plaintext_kek_never_exposed_to_application":True,"provider_audit_logging":True,"key_rotation_supported":True,"previous_key_versions_retained_for_authorized_decrypt":True,"iam_role_separation":True,"key_admin_separate_from_crypto_user":True,"restore_approver_separate_from_crypto_user":True,"deletion_protection_or_delayed_destruction":True,"explicit_region_and_residency_configuration":True,"private_network_path_or_equivalent_restriction":True,"no_key_material_in_repository":True,"no_key_material_in_backup_manifest":True,"no_key_material_in_stdout":True,"production_enabled":True}
T={"version":"1.0","evidence_as_of":"2026-09-08","entitlement_status":"EXPLICITLY_APPROVED","applicant_eligibility_status":"EXPLICITLY_APPROVED","exact_micro_product_status":"EXPLICITLY_APPROVED","provider_selected_status":"EXPLICITLY_APPROVED","read_only_transport_status":"EXPLICITLY_APPROVED","broker_auth_used":False,"trading_permission_used":False,"ose_third_party_cloud_processing_status":"EXPLICITLY_APPROVED","provider_third_party_cloud_processing_status":"EXPLICITLY_APPROVED","service_facilitator_required":True,"service_facilitator_approval_status":"EXPLICITLY_APPROVED","encrypted_backup_creation_status":"EXPLICITLY_APPROVED","encrypted_backup_storage_status":"EXPLICITLY_APPROVED","backup_region_status":"EXPLICITLY_APPROVED","backup_retention_terms_status":"EXPLICITLY_CONFIRMED","backup_deletion_terms_status":"EXPLICITLY_CONFIRMED","restore_permission_status":"EXPLICITLY_APPROVED","dr_drill_permission_status":"EXPLICITLY_APPROVED","kms_hsm_key_custody_status":"EXPLICITLY_APPROVED","incident_reporting_terms_status":"EXPLICITLY_CONFIRMED","audit_cooperation_terms_status":"EXPLICITLY_CONFIRMED","public_output_requested":False}
tests={}
def ready(n,k,t):tests[n]=m.evaluate(k,t)["status"]=="READY_FOR_REAL_ENCRYPTED_BACKUP_PRIVATE_ONLY"
def blocked(n,k,t,needle):r=m.evaluate(k,t);tests[n]=r["status"]=="BLOCKED" and any(needle in x for x in r["blockers"])
ready("managed_hsm_complete_ready",copy.deepcopy(K),copy.deepcopy(T))
k=copy.deepcopy(K);k["control_class"]="DEDICATED_HSM_OR_CUSTOM_KEY_STORE";ready("dedicated_hsm_complete_ready",k,copy.deepcopy(T))
for name,field,val,needle in [
 ("file_keyring_rejected","control_class","SYNTHETIC_FILE_KEYRING","PROHIBITED_KEY_CUSTODY_CLASS"),
 ("unselected_class_blocked","control_class","UNSELECTED","PRODUCTION_KEY_CUSTODY_CLASS_NOT_SELECTED"),
 ("exportable_kek_blocked","kek_non_exportable",False,"KEK_NON_EXPORTABLE"),
 ("no_hsm_blocked","hsm_backed",False,"HSM_BACKED"),
 ("fips_too_low_blocked","fips_security_level",2,"FIPS_SECURITY_LEVEL"),
 ("no_audit_blocked","provider_audit_logging",False,"PROVIDER_AUDIT_LOGGING"),
 ("no_rotation_blocked","key_rotation_supported",False,"KEY_ROTATION_SUPPORTED"),
 ("no_role_separation_blocked","iam_role_separation",False,"IAM_ROLE_SEPARATION"),
 ("restore_role_not_separate_blocked","restore_approver_separate_from_crypto_user",False,"RESTORE_APPROVER"),
 ("region_unselected_blocked","region","UNSELECTED","REGION_UNSELECTED"),
 ("vendor_unselected_blocked","vendor","UNSELECTED","VENDOR_UNSELECTED"),
 ("production_disabled_blocked","production_enabled",False,"NOT_ENABLED")
]:
    k=copy.deepcopy(K);k[field]=val;blocked(name,k,copy.deepcopy(T),needle)
for name,field,val,needle in [
 ("entitlement_unresolved","entitlement_status","UNRESOLVED","ENTITLEMENT_STATUS"),
 ("micro_unresolved","exact_micro_product_status","UNRESOLVED","EXACT_MICRO_PRODUCT_STATUS"),
 ("ose_cloud_unresolved","ose_third_party_cloud_processing_status","UNRESOLVED","OSE_THIRD_PARTY_CLOUD_PROCESSING_STATUS"),
 ("provider_cloud_unresolved","provider_third_party_cloud_processing_status","UNRESOLVED","PROVIDER_THIRD_PARTY_CLOUD_PROCESSING_STATUS"),
 ("backup_creation_unresolved","encrypted_backup_creation_status","UNRESOLVED","ENCRYPTED_BACKUP_CREATION_STATUS"),
 ("retention_unresolved","backup_retention_terms_status","UNRESOLVED","BACKUP_RETENTION_TERMS_STATUS"),
 ("restore_unresolved","restore_permission_status","UNRESOLVED","RESTORE_PERMISSION_STATUS"),
 ("drill_unresolved","dr_drill_permission_status","UNRESOLVED","DR_DRILL_PERMISSION_STATUS"),
 ("region_terms_unresolved","backup_region_status","UNRESOLVED","BACKUP_REGION_STATUS"),
 ("key_custody_terms_unresolved","kms_hsm_key_custody_status","UNRESOLVED","KMS_HSM_KEY_CUSTODY_STATUS"),
 ("broker_auth_rejected","broker_auth_used",True,"BROKER_AUTH_PROHIBITED"),
 ("trading_permission_rejected","trading_permission_used",True,"TRADING_PERMISSION_PROHIBITED"),
 ("public_output_rejected","public_output_requested",True,"PUBLIC_OUTPUT_NOT_AUTHORIZED")
]:
    t=copy.deepcopy(T);t[field]=val;blocked(name,copy.deepcopy(K),t,needle)
t=copy.deepcopy(T);t["service_facilitator_approval_status"]="UNRESOLVED";blocked("service_facilitator_unapproved",copy.deepcopy(K),t,"SERVICE_FACILITATOR_APPROVAL_NOT_READY")
t=copy.deepcopy(T);t["service_facilitator_required"]=False;t["service_facilitator_approval_status"]="NOT_REQUIRED";ready("service_facilitator_not_required_ready",copy.deepcopy(K),t)
currentK=json.loads((ROOT/"config"/"jnu_production_key_custody_current_v1.json").read_text());currentT=json.loads((ROOT/"config"/"jnu_provider_term_readiness_current_v1.json").read_text())
r=m.evaluate(currentK,currentT);tests["current_state_fail_closed"]=r["status"]=="BLOCKED" and r["real_entitled_backup_activation_permitted"] is False and len(r["blockers"])>=10
status="PASS" if all(tests.values()) else "FAIL";print(json.dumps({"status":status,"tests":tests,"passed":sum(tests.values()),"total":len(tests)},indent=2));raise SystemExit(0 if status=="PASS" else 1)
