from __future__ import annotations
import copy, hashlib, json, tempfile
from pathlib import Path
from decide_jnu_private_vendor_pair_selection_authorization_v1 import ROOT, process, evaluate_request, validate_production_state, load, sha256_file

MEMORY=ROOT/"config"/"jnu_operational_framework_cross_session_memory_v1.json"
PROTO=ROOT/"config"/"jnu_private_vendor_pair_selection_authorization_protocol_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"

def w(p:Path,x): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+"\n",encoding="utf-8")
def rejected(fn)->bool:
    try: fn();return False
    except Exception:return True

short=load(SHORTLIST);proto=load(PROTO);T={}
pairs=[p["id"]+"__"+k["id"] for p in short["market_data_candidates"] for k in short["key_custody_candidates"]]
with tempfile.TemporaryDirectory(prefix="jnu-selection-auth-") as td0:
    td=Path(td0);store=td/"store";store.mkdir()
    results=[]
    for i,cid in enumerate(pairs):
        results.append({
          "combination_id":cid,
          "dossier_sha256":hashlib.sha256(("dossier-"+cid).encode()).hexdigest(),
          "outcome":"SYNTHETIC_DUAL_CONTROL_APPROVED_NOT_ACTIVATABLE",
          "underlying_synthetic_evidence_complete":True,
          "reviews":[
            {"review_id":f"R{i}E","reviewer_role":"EVIDENCE_REVIEWER","reviewer_ref_sha256":hashlib.sha256(f"e{i}".encode()).hexdigest(),"disposition":"APPROVE","reviewed_at_utc":"2026-09-08T01:00:00+00:00","revalidation_due_at_utc":"2026-09-15T01:00:00+00:00","expires_at_utc":"2026-09-22T01:00:00+00:00","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"},
            {"review_id":f"R{i}C","reviewer_role":"CONTROL_REVIEWER","reviewer_ref_sha256":hashlib.sha256(f"c{i}".encode()).hexdigest(),"disposition":"APPROVE","reviewed_at_utc":"2026-09-08T01:01:00+00:00","revalidation_due_at_utc":"2026-09-15T01:01:00+00:00","expires_at_utc":"2026-09-22T01:01:00+00:00","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"}
          ],
          "activation_blockers":["SYNTHETIC_ONLY_REVIEW","MARKET_DATA_PROVIDER_NOT_SELECTED","KMS_PROVIDER_NOT_SELECTED","PRODUCTION_KEY_PROFILE_DISABLED","REAL_CREDENTIALS_NOT_CONNECTED","REAL_ACTIVATION_MANIFEST_NOT_GENERATED"],
          "selected":False,"real_activation_authorized":False
        })
    receipt={
      "version":"1.0","artifact_class":"JNU_REDACTED_SYNTHETIC_DUAL_CONTROL_REVIEW_RECEIPT","storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,"mode":"SYNTHETIC","review_batch_id":"JNU_REVIEW_SYNTH_SELECTION","evaluation_at_utc":"2026-09-08T02:00:00+00:00",
      "composite_dossier_sha256":hashlib.sha256(b"composite").hexdigest(),"combination_count":6,"review_count":12,"results":results,
      "reviewer_ids_emitted":False,"ranking_generated":False,"recommendation_generated":False,"selection_generated":False,
      "market_data_provider_selected":False,"kms_provider_selected":False,"production_key_profile_enabled":False,"real_provider_terms_ready":False,
      "credentials_connected":False,"real_activation_manifest_generated":False,"real_activation_authorized":False
    }
    rp=td/"receipt.json";w(rp,receipt)
    target=pairs[0]
    auth={
      "version":"1.0","artifact_class":"JNU_SYNTHETIC_USER_SELECTION_AUTHORIZATION","mode":"SYNTHETIC","synthetic_fixture":True,
      "authorization_id":"JNU_AUTH_SYNTH_001","authorization_scope":"VENDOR_PAIR_SELECTION","authorization_status":"SYNTHETIC_DISABLED",
      "authorizer_role":"USER_PRINCIPAL","authorizer_reference":"synthetic-user-principal","authorizer_attestation":"EXPLICIT_SYNTHETIC_AUTHORIZATION_RECORDED_DISABLED",
      "review_batch_id":receipt["review_batch_id"],"review_receipt_sha256":sha256_file(rp),"composite_dossier_sha256":receipt["composite_dossier_sha256"],
      "authorized_combination_id":target,"issued_at_utc":"2026-09-08T02:05:00+00:00","valid_from_utc":"2026-09-08T02:10:00+00:00",
      "expires_at_utc":"2026-09-09T02:10:00+00:00","selection_write_permitted":False,"real_selection_authorized":False
    }
    ap=td/"auth.json";w(ap,auth)
    req={
      "version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,"decision_id":"JNU_SELECTION_DECISION_SYNTH_001",
      "decision_at_utc":"2026-09-08T03:00:00+00:00","requested_combination_id":target,
      "review_receipt_path":str(rp.resolve()),"review_receipt_sha256":sha256_file(rp),
      "authorization_path":str(ap.resolve()),"authorization_sha256":sha256_file(ap)
    }
    qp=td/"request.json";w(qp,req)
    r1=process(qp,store);decision_path=store/"selection_decisions"/(req["decision_id"]+".json");decision=load(decision_path);raw=decision_path.read_text(encoding="utf-8")
    T["baseline_decision_written"]=r1["status"]=="SYNTHETIC_SELECTION_DECISION_RECORDED"
    T["authorization_binding_validated"]=decision["authorization_binding_validated"] is True
    T["dual_control_validated"]=decision["dual_control_approval_validated"] is True
    T["six_pair_coverage_validated"]=decision["exact_six_pair_coverage_validated"] is True
    T["selection_transition_prohibited"]=decision["selection_transition_permitted"] is False
    T["selection_not_written"]=decision["selection_written"] is False
    T["selected_pair_remains_unselected"]=decision["selected_combination_id"]=="UNSELECTED" and decision["selected_market_data_provider"]=="UNSELECTED" and decision["selected_key_custody_provider"]=="UNSELECTED"
    T["production_state_not_mutated"]=decision["production_state_mutated"] is False
    T["real_activation_false"]=decision["real_activation_authorized"] is False
    T["authorizer_reference_redacted"]=decision["authorizer_ref_sha256"] and "synthetic-user-principal" not in raw
    r2=process(qp,store)
    T["exact_replay_idempotent"]=r2["status"]=="IDEMPOTENT_REPLAY_ACCEPTED" and r2["decision_record_sha256"]==r1["decision_record_sha256"]

    missing=copy.deepcopy(req);missing["authorization_path"]=str((td/"missing-auth.json").resolve())
    T["missing_authorization_rejected"]=rejected(lambda:evaluate_request(missing))
    bad=copy.deepcopy(req);bad["authorization_sha256"]="0"*64
    T["wrong_authorization_hash_rejected"]=rejected(lambda:evaluate_request(bad))
    bad=copy.deepcopy(req);bad["review_receipt_sha256"]="0"*64
    T["wrong_receipt_hash_rejected"]=rejected(lambda:evaluate_request(bad))

    tampered=copy.deepcopy(receipt);tampered["review_count"]=11;trp=td/"tampered-receipt.json";w(trp,tampered)
    bad=copy.deepcopy(req);bad["review_receipt_path"]=str(trp.resolve())
    T["receipt_tamper_rejected_by_bound_hash"]=rejected(lambda:evaluate_request(bad))

    wrongclass=copy.deepcopy(receipt);wrongclass["artifact_class"]="WRONG";wrp=td/"wrong-class.json";w(wrp,wrongclass)
    bad=copy.deepcopy(req);bad["review_receipt_path"]=str(wrp.resolve());bad["review_receipt_sha256"]=sha256_file(wrp)
    T["wrong_receipt_class_rejected"]=rejected(lambda:evaluate_request(bad))
    selected=copy.deepcopy(receipt);selected["selection_generated"]=True;srp=td/"selected-receipt.json";w(srp,selected)
    bad=copy.deepcopy(req);bad["review_receipt_path"]=str(srp.resolve());bad["review_receipt_sha256"]=sha256_file(srp)
    T["receipt_selection_flag_rejected"]=rejected(lambda:evaluate_request(bad))
    pairselected=copy.deepcopy(receipt);pairselected["results"][0]["selected"]=True;prp=td/"pair-selected.json";w(prp,pairselected)
    bad=copy.deepcopy(req);bad["review_receipt_path"]=str(prp.resolve());bad["review_receipt_sha256"]=sha256_file(prp)
    T["selected_pair_in_receipt_rejected"]=rejected(lambda:evaluate_request(bad))
    activated=copy.deepcopy(receipt);activated["real_activation_authorized"]=True;arp=td/"activated-receipt.json";w(arp,activated)
    bad=copy.deepcopy(req);bad["review_receipt_path"]=str(arp.resolve());bad["review_receipt_sha256"]=sha256_file(arp)
    T["activated_receipt_rejected"]=rejected(lambda:evaluate_request(bad))
    missingcombo=copy.deepcopy(receipt);missingcombo["results"]=missingcombo["results"][:-1];missingcombo["combination_count"]=5;mrp=td/"missing-combo.json";w(mrp,missingcombo)
    bad=copy.deepcopy(req);bad["review_receipt_path"]=str(mrp.resolve());bad["review_receipt_sha256"]=sha256_file(mrp)
    T["missing_combination_rejected"]=rejected(lambda:evaluate_request(bad))
    dupcombo=copy.deepcopy(receipt);dupcombo["results"][-1]=copy.deepcopy(dupcombo["results"][0]);drp=td/"dup-combo.json";w(drp,dupcombo)
    bad=copy.deepcopy(req);bad["review_receipt_path"]=str(drp.resolve());bad["review_receipt_sha256"]=sha256_file(drp)
    T["duplicate_combination_rejected"]=rejected(lambda:evaluate_request(bad))

    stale=copy.deepcopy(req);stale["decision_at_utc"]="2026-09-16T03:00:00+00:00"
    T["stale_review_receipt_rejected"]=rejected(lambda:evaluate_request(stale))
    expired=copy.deepcopy(req);expired["decision_at_utc"]="2026-09-23T03:00:00+00:00"
    T["expired_review_receipt_rejected"]=rejected(lambda:evaluate_request(expired))
    rejectedreceipt=copy.deepcopy(receipt);rejectedreceipt["results"][0]["outcome"]="SYNTHETIC_DUAL_CONTROL_REJECTED";rrp=td/"rejected-pair.json";w(rrp,rejectedreceipt)
    bad=copy.deepcopy(req);bad["review_receipt_path"]=str(rrp.resolve());bad["review_receipt_sha256"]=sha256_file(rrp)
    bad_auth=copy.deepcopy(auth);bad_auth["review_receipt_sha256"]=sha256_file(rrp);bap=td/"auth-rejected-pair.json";w(bap,bad_auth);bad["authorization_path"]=str(bap.resolve());bad["authorization_sha256"]=sha256_file(bap)
    T["requested_pair_without_dual_approval_rejected"]=rejected(lambda:evaluate_request(bad))
    unknown=copy.deepcopy(req);unknown["requested_combination_id"]="UNKNOWN__PAIR"
    T["unknown_requested_pair_rejected"]=rejected(lambda:evaluate_request(unknown))

    substitution=copy.deepcopy(req);substitution["requested_combination_id"]=pairs[1]
    T["unauthorized_pair_substitution_rejected"]=rejected(lambda:evaluate_request(substitution))
    ah=copy.deepcopy(auth);ah["review_receipt_sha256"]="0"*64;ahp=td/"auth-wrong-receipt.json";w(ahp,ah);bad=copy.deepcopy(req);bad["authorization_path"]=str(ahp.resolve());bad["authorization_sha256"]=sha256_file(ahp)
    T["authorization_receipt_hash_conflict_rejected"]=rejected(lambda:evaluate_request(bad))
    ab=copy.deepcopy(auth);ab["review_batch_id"]="OTHER";abp=td/"auth-wrong-batch.json";w(abp,ab);bad=copy.deepcopy(req);bad["authorization_path"]=str(abp.resolve());bad["authorization_sha256"]=sha256_file(abp)
    T["authorization_review_batch_conflict_rejected"]=rejected(lambda:evaluate_request(bad))
    ac=copy.deepcopy(auth);ac["composite_dossier_sha256"]="0"*64;acp=td/"auth-wrong-composite.json";w(acp,ac);bad=copy.deepcopy(req);bad["authorization_path"]=str(acp.resolve());bad["authorization_sha256"]=sha256_file(acp)
    T["authorization_composite_hash_conflict_rejected"]=rejected(lambda:evaluate_request(bad))
    aexp=copy.deepcopy(auth);aexp["expires_at_utc"]="2026-09-08T02:30:00+00:00";aep=td/"auth-expired.json";w(aep,aexp);bad=copy.deepcopy(req);bad["authorization_path"]=str(aep.resolve());bad["authorization_sha256"]=sha256_file(aep)
    T["expired_authorization_rejected"]=rejected(lambda:evaluate_request(bad))
    anf=copy.deepcopy(auth);anf["valid_from_utc"]="2026-09-08T04:00:00+00:00";anp=td/"auth-not-yet.json";w(anp,anf);bad=copy.deepcopy(req);bad["authorization_path"]=str(anp.resolve());bad["authorization_sha256"]=sha256_file(anp)
    T["not_yet_valid_authorization_rejected"]=rejected(lambda:evaluate_request(bad))
    ant=copy.deepcopy(auth);ant["issued_at_utc"]="2026-09-08T02:05:00";atp=td/"auth-naive.json";w(atp,ant);bad=copy.deepcopy(req);bad["authorization_path"]=str(atp.resolve());bad["authorization_sha256"]=sha256_file(atp)
    T["naive_authorization_time_rejected"]=rejected(lambda:evaluate_request(bad))
    aenabled=copy.deepcopy(auth);aenabled["authorization_status"]="SYNTHETIC_ENABLED";aenp=td/"auth-enabled.json";w(aenp,aenabled);bad=copy.deepcopy(req);bad["authorization_path"]=str(aenp.resolve());bad["authorization_sha256"]=sha256_file(aenp)
    T["enabled_authorization_rejected_in_synthetic_stage"]=rejected(lambda:evaluate_request(bad))
    awrite=copy.deepcopy(auth);awrite["selection_write_permitted"]=True;awp=td/"auth-write.json";w(awp,awrite);bad=copy.deepcopy(req);bad["authorization_path"]=str(awp.resolve());bad["authorization_sha256"]=sha256_file(awp)
    T["selection_write_permission_rejected"]=rejected(lambda:evaluate_request(bad))
    areal=copy.deepcopy(auth);areal["real_selection_authorized"]=True;arp2=td/"auth-real.json";w(arp2,areal);bad=copy.deepcopy(req);bad["authorization_path"]=str(arp2.resolve());bad["authorization_sha256"]=sha256_file(arp2)
    T["real_selection_authorization_rejected"]=rejected(lambda:evaluate_request(bad))
    ar=copy.deepcopy(auth);ar["authorizer_role"]="OTHER";arp3=td/"auth-role.json";w(arp3,ar);bad=copy.deepcopy(req);bad["authorization_path"]=str(arp3.resolve());bad["authorization_sha256"]=sha256_file(arp3)
    T["wrong_authorizer_role_rejected"]=rejected(lambda:evaluate_request(bad))
    aa=copy.deepcopy(auth);aa["authorizer_attestation"]="INFERRED";aap=td/"auth-inferred.json";w(aap,aa);bad=copy.deepcopy(req);bad["authorization_path"]=str(aap.resolve());bad["authorization_sha256"]=sha256_file(aap)
    T["inferred_authorization_rejected"]=rejected(lambda:evaluate_request(bad))
    aref=copy.deepcopy(auth);aref["authorizer_reference"]="";arfp=td/"auth-empty-ref.json";w(arfp,aref);bad=copy.deepcopy(req);bad["authorization_path"]=str(arfp.resolve());bad["authorization_sha256"]=sha256_file(arfp)
    T["empty_authorizer_reference_rejected"]=rejected(lambda:evaluate_request(bad))

    # Same decision id, different but otherwise valid target+authorization must collide with immutable record.
    target2=pairs[1];auth2=copy.deepcopy(auth);auth2["authorization_id"]="JNU_AUTH_SYNTH_002";auth2["authorized_combination_id"]=target2;a2p=td/"auth2.json";w(a2p,auth2)
    req2=copy.deepcopy(req);req2["requested_combination_id"]=target2;req2["authorization_path"]=str(a2p.resolve());req2["authorization_sha256"]=sha256_file(a2p)
    q2p=td/"request2-same-id.json";w(q2p,req2)
    T["same_decision_id_different_content_replay_rejected"]=rejected(lambda:process(q2p,store))

    T["repo_internal_request_rejected"]=rejected(lambda:process(ROOT/"config/jnu_private_composite_evidence_dual_control_checkpoint_v1.json",store))
    T["repo_internal_decision_store_rejected"]=rejected(lambda:process(qp,ROOT/"selection-store-forbidden"))

    key=load(KEY_CURRENT);terms=load(TERMS_CURRENT);short2=load(SHORTLIST)
    sm=copy.deepcopy(short2);sm["selected_market_data_provider"]=short2["market_data_candidates"][0]["id"]
    T["market_data_selection_state_mutation_rejected"]=rejected(lambda:validate_production_state(sm,key,terms,proto))
    sk=copy.deepcopy(short2);sk["selected_key_custody_provider"]=short2["key_custody_candidates"][0]["id"]
    T["kms_selection_state_mutation_rejected"]=rejected(lambda:validate_production_state(sk,key,terms,proto))
    km=copy.deepcopy(key);km["production_enabled"]=True
    T["production_key_enablement_mutation_rejected"]=rejected(lambda:validate_production_state(short2,km,terms,proto))
    kv=copy.deepcopy(key);kv["vendor"]="AWS"
    T["production_key_vendor_mutation_rejected"]=rejected(lambda:validate_production_state(short2,kv,terms,proto))
    kr=copy.deepcopy(key);kr["region"]="ap-northeast-1"
    T["production_key_region_mutation_rejected"]=rejected(lambda:validate_production_state(short2,kr,terms,proto))
    tb=copy.deepcopy(terms);tb["broker_auth_used"]=True
    T["broker_auth_mutation_rejected"]=rejected(lambda:validate_production_state(short2,key,tb,proto))
    tt=copy.deepcopy(terms);tt["trading_permission_used"]=True
    T["trading_permission_mutation_rejected"]=rejected(lambda:validate_production_state(short2,key,tt,proto))
    tp=copy.deepcopy(terms);tp["public_output_requested"]=True
    T["public_output_mutation_rejected"]=rejected(lambda:validate_production_state(short2,key,tp,proto))

mem=load(MEMORY);key=load(KEY_CURRENT);terms=load(TERMS_CURRENT);short2=load(SHORTLIST)
T["public_real_ledger_still_zero_zero"]=mem.get("real_live_shadow_forecasts_registered")==0 and mem.get("real_live_shadow_outcomes_registered")==0
T["shortlist_still_unselected"]=short2.get("selected_market_data_provider")=="UNSELECTED" and short2.get("selected_key_custody_provider")=="UNSELECTED"
T["production_key_still_unselected_disabled"]=key.get("production_enabled") is False and key.get("vendor")=="UNSELECTED" and key.get("region")=="UNSELECTED"
T["real_provider_terms_still_unresolved"]=any(v=="UNRESOLVED" for k,v in terms.items() if k.endswith("_status"))
status="PASS" if all(T.values()) else "FAIL"
print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T)},indent=2))
raise SystemExit(0 if status=="PASS" else 1)
