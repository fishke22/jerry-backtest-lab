from __future__ import annotations
import copy, hashlib, json, shutil, tempfile
from pathlib import Path
from decide_jnu_private_selection_with_lifecycle_current_auth_v1 import ROOT, process, evaluate_request, load, sha256_file
from manage_jnu_private_vendor_pair_authorization_lifecycle_v1 import process as lifecycle_process, audit_chain

MEMORY=ROOT/"config"/"jnu_operational_framework_cross_session_memory_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"

def w(p:Path,x): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+"\n",encoding="utf-8")
def rejected(fn)->bool:
    try: fn();return False
    except Exception:return True

short=load(SHORTLIST);pairs=[p["id"]+"__"+k["id"] for p in short["market_data_candidates"] for k in short["key_custody_candidates"]];T={}
with tempfile.TemporaryDirectory(prefix="jnu-life-integrated-selection-") as td0:
    td=Path(td0);life=td/"life";life.mkdir();decisions=td/"decisions";decisions.mkdir()
    results=[]
    for i,cid in enumerate(pairs):
        results.append({
          "combination_id":cid,"dossier_sha256":hashlib.sha256(("dossier-"+cid).encode()).hexdigest(),
          "outcome":"SYNTHETIC_DUAL_CONTROL_APPROVED_NOT_ACTIVATABLE","underlying_synthetic_evidence_complete":True,
          "reviews":[
            {"review_id":f"R{i}E","reviewer_role":"EVIDENCE_REVIEWER","reviewer_ref_sha256":hashlib.sha256(f"e{i}".encode()).hexdigest(),"disposition":"APPROVE","reviewed_at_utc":"2026-09-08T01:00:00+00:00","revalidation_due_at_utc":"2026-09-15T01:00:00+00:00","expires_at_utc":"2026-09-22T01:00:00+00:00","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"},
            {"review_id":f"R{i}C","reviewer_role":"CONTROL_REVIEWER","reviewer_ref_sha256":hashlib.sha256(f"c{i}".encode()).hexdigest(),"disposition":"APPROVE","reviewed_at_utc":"2026-09-08T01:01:00+00:00","revalidation_due_at_utc":"2026-09-15T01:01:00+00:00","expires_at_utc":"2026-09-22T01:01:00+00:00","reviewer_attestation":"EXPLICIT_TEXT_CONFIRMED"}
          ],
          "activation_blockers":["SYNTHETIC_ONLY_REVIEW","MARKET_DATA_PROVIDER_NOT_SELECTED","KMS_PROVIDER_NOT_SELECTED","PRODUCTION_KEY_PROFILE_DISABLED","REAL_CREDENTIALS_NOT_CONNECTED","REAL_ACTIVATION_MANIFEST_NOT_GENERATED"],
          "selected":False,"real_activation_authorized":False
        })
    receipt={
      "version":"1.0","artifact_class":"JNU_REDACTED_SYNTHETIC_DUAL_CONTROL_REVIEW_RECEIPT","storage_scope":"PRIVATE_INTERNAL_ONLY",
      "public_distribution_permitted":False,"mode":"SYNTHETIC","review_batch_id":"JNU_REVIEW_SYNTH_LIFE_INTEGRATION","evaluation_at_utc":"2026-09-08T02:00:00+00:00",
      "composite_dossier_sha256":hashlib.sha256(b"composite").hexdigest(),"combination_count":6,"review_count":12,"results":results,
      "reviewer_ids_emitted":False,"ranking_generated":False,"recommendation_generated":False,"selection_generated":False,
      "market_data_provider_selected":False,"kms_provider_selected":False,"production_key_profile_enabled":False,"real_provider_terms_ready":False,
      "credentials_connected":False,"real_activation_manifest_generated":False,"real_activation_authorized":False
    }
    rp=td/"receipt.json";w(rp,receipt)

    def make_auth(aid,pair,issued="2026-09-08T02:05:00+00:00",valid="2026-09-08T02:10:00+00:00",expiry="2026-09-12T00:00:00+00:00"):
        return {
          "version":"1.0","artifact_class":"JNU_SYNTHETIC_USER_SELECTION_AUTHORIZATION","mode":"SYNTHETIC","synthetic_fixture":True,
          "authorization_id":aid,"authorization_scope":"VENDOR_PAIR_SELECTION","authorization_status":"SYNTHETIC_DISABLED",
          "authorizer_role":"USER_PRINCIPAL","authorizer_reference":"synthetic-user-"+aid,"authorizer_attestation":"EXPLICIT_SYNTHETIC_AUTHORIZATION_RECORDED_DISABLED",
          "review_batch_id":receipt["review_batch_id"],"review_receipt_sha256":sha256_file(rp),"composite_dossier_sha256":receipt["composite_dossier_sha256"],
          "authorized_combination_id":pair,"issued_at_utc":issued,"valid_from_utc":valid,"expires_at_utc":expiry,
          "selection_write_permitted":False,"real_selection_authorized":False
        }
    a1=make_auth("JNU_AUTH_SYNTH_INT_A1",pairs[0]);a1p=td/"a1.json";w(a1p,a1)
    issue={
      "version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,"event_id":"JNU_AUTH_EVENT_SYNTH_INT_001","event_type":"ISSUE","event_at_utc":"2026-09-08T02:20:00+00:00",
      "authorization_path":str(a1p.resolve()),"authorization_sha256":sha256_file(a1p),"target_authorization_id":None,
      "revocation_reason":None,"revocation_authorizer_reference":None,"revocation_authorizer_role":None,"revocation_attestation":None
    }
    ip=td/"issue.json";w(ip,issue);lifecycle_process(ip,life);s1=audit_chain(life)
    req={
      "version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,"decision_id":"JNU_SELECTION_DECISION_SYNTH_LIFE_001",
      "decision_at_utc":"2026-09-08T03:00:00+00:00","requested_combination_id":pairs[0],
      "review_receipt_path":str(rp.resolve()),"review_receipt_sha256":sha256_file(rp),
      "authorization_path":str(a1p.resolve()),"authorization_sha256":sha256_file(a1p),
      "lifecycle_store_root":str(life.resolve()),"lifecycle_expected_event_count":1,"lifecycle_expected_head_sha256":s1["last_event_sha256"]
    }
    qp=td/"request.json";w(qp,req);r1=process(qp,decisions)
    dp=decisions/"selection_lifecycle_decisions"/(req["decision_id"]+".json");d=load(dp);raw=dp.read_text(encoding="utf-8")
    T["baseline_integrated_decision_written"]=r1["status"]=="SYNTHETIC_LIFECYCLE_SELECTION_DECISION_RECORDED"
    T["full_chain_validated"]=d["lifecycle_full_chain_validated"] is True
    T["event_backups_validated"]=d["lifecycle_event_backups_validated"] is True
    T["current_authorization_validated"]=d["lifecycle_current_authorization_validated"] is True
    T["base_receipt_and_authorization_gates_preserved"]=d["base_authorization_binding_validated"] is True and d["dual_control_approval_validated"] is True and d["exact_six_pair_coverage_validated"] is True
    T["head_and_count_emitted"]=d["lifecycle_event_count"]==1 and d["lifecycle_head_sha256"]==s1["last_event_sha256"]
    T["lifecycle_path_not_emitted"]=str(life.resolve()) not in raw
    T["selection_still_prohibited"]=d["selection_transition_permitted"] is False and d["selection_written"] is False and d["selected_combination_id"]=="UNSELECTED"
    T["production_and_activation_still_false"]=d["production_state_mutated"] is False and d["real_activation_authorized"] is False
    T["exact_replay_idempotent"]=process(qp,decisions)["status"]=="IDEMPOTENT_REPLAY_ACCEPTED"

    bad=copy.deepcopy(req);bad["lifecycle_expected_event_count"]=2
    T["event_count_binding_mismatch_rejected"]=rejected(lambda:evaluate_request(bad))
    bad=copy.deepcopy(req);bad["lifecycle_expected_head_sha256"]="0"*64
    T["head_hash_binding_mismatch_rejected"]=rejected(lambda:evaluate_request(bad))
    bad=copy.deepcopy(req);bad["lifecycle_store_root"]=str((td/"missing-life").resolve())
    T["missing_lifecycle_rejected"]=rejected(lambda:evaluate_request(bad))
    bad=copy.deepcopy(req);bad["authorization_sha256"]="0"*64
    T["base_authorization_hash_gate_preserved"]=rejected(lambda:evaluate_request(bad))
    bad=copy.deepcopy(req);bad["review_receipt_sha256"]="0"*64
    T["base_receipt_hash_gate_preserved"]=rejected(lambda:evaluate_request(bad))
    bad=copy.deepcopy(req);bad["requested_combination_id"]=pairs[1]
    T["base_pair_binding_gate_preserved"]=rejected(lambda:evaluate_request(bad))

    # Supersede A1 -> A2; old authorization must immediately fail, new one succeeds.
    a2=make_auth("JNU_AUTH_SYNTH_INT_A2",pairs[0],"2026-09-08T03:05:00+00:00","2026-09-08T03:10:00+00:00","2026-09-13T00:00:00+00:00");a2p=td/"a2.json";w(a2p,a2)
    sup={
      "version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,"event_id":"JNU_AUTH_EVENT_SYNTH_INT_002","event_type":"SUPERSEDE","event_at_utc":"2026-09-08T03:20:00+00:00",
      "authorization_path":str(a2p.resolve()),"authorization_sha256":sha256_file(a2p),"target_authorization_id":a1["authorization_id"],
      "revocation_reason":None,"revocation_authorizer_reference":None,"revocation_authorizer_role":None,"revocation_attestation":None
    }
    sp=td/"sup.json";w(sp,sup);lifecycle_process(sp,life);s2=audit_chain(life)
    old=copy.deepcopy(req);old["decision_id"]="JNU_SELECTION_DECISION_SYNTH_LIFE_OLD";old["decision_at_utc"]="2026-09-08T04:00:00+00:00";old["lifecycle_expected_event_count"]=2;old["lifecycle_expected_head_sha256"]=s2["last_event_sha256"]
    T["superseded_authorization_rejected"]=rejected(lambda:evaluate_request(old))
    new=copy.deepcopy(old);new["decision_id"]="JNU_SELECTION_DECISION_SYNTH_LIFE_A2";new["authorization_path"]=str(a2p.resolve());new["authorization_sha256"]=sha256_file(a2p);np=td/"new.json";w(np,new)
    T["current_superseding_authorization_accepted"]=process(np,decisions)["status"]=="SYNTHETIC_LIFECYCLE_SELECTION_DECISION_RECORDED"

    # Revoke A2; no current authorization can authorize a decision.
    rev={
      "version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,"event_id":"JNU_AUTH_EVENT_SYNTH_INT_003","event_type":"REVOKE","event_at_utc":"2026-09-08T04:20:00+00:00",
      "authorization_path":None,"authorization_sha256":None,"target_authorization_id":a2["authorization_id"],
      "revocation_reason":"SYNTHETIC_INTEGRATION_TEST","revocation_authorizer_reference":"synthetic-revoker",
      "revocation_authorizer_role":"USER_PRINCIPAL","revocation_attestation":"EXPLICIT_SYNTHETIC_REVOCATION_RECORDED"
    }
    rvp=td/"revoke.json";w(rvp,rev);lifecycle_process(rvp,life);s3=audit_chain(life)
    revoked=copy.deepcopy(new);revoked["decision_id"]="JNU_SELECTION_DECISION_SYNTH_LIFE_REVOKED";revoked["decision_at_utc"]="2026-09-08T05:00:00+00:00";revoked["lifecycle_expected_event_count"]=3;revoked["lifecycle_expected_head_sha256"]=s3["last_event_sha256"]
    T["revoked_authorization_rejected"]=rejected(lambda:evaluate_request(revoked))

    # New ISSUE after revoke, then expiry at decision time.
    a3=make_auth("JNU_AUTH_SYNTH_INT_A3",pairs[1],"2026-09-08T05:05:00+00:00","2026-09-08T05:10:00+00:00","2026-09-09T00:00:00+00:00");a3p=td/"a3.json";w(a3p,a3)
    issue3=copy.deepcopy(issue);issue3["event_id"]="JNU_AUTH_EVENT_SYNTH_INT_004";issue3["event_at_utc"]="2026-09-08T05:20:00+00:00";issue3["authorization_path"]=str(a3p.resolve());issue3["authorization_sha256"]=sha256_file(a3p)
    i3p=td/"issue3.json";w(i3p,issue3);lifecycle_process(i3p,life);s4=audit_chain(life)
    exp=copy.deepcopy(req);exp["decision_id"]="JNU_SELECTION_DECISION_SYNTH_LIFE_EXPIRED";exp["decision_at_utc"]="2026-09-09T01:00:00+00:00";exp["requested_combination_id"]=pairs[1];exp["authorization_path"]=str(a3p.resolve());exp["authorization_sha256"]=sha256_file(a3p);exp["lifecycle_expected_event_count"]=4;exp["lifecycle_expected_head_sha256"]=s4["last_event_sha256"]
    T["expired_current_authorization_rejected"]=rejected(lambda:evaluate_request(exp))

    # Future lifecycle event relative to decision time is rejected even if chain itself is valid.
    future=copy.deepcopy(exp);future["decision_id"]="JNU_SELECTION_DECISION_SYNTH_LIFE_FUTURE";future["decision_at_utc"]="2026-09-08T05:15:00+00:00"
    T["future_event_relative_to_decision_rejected"]=rejected(lambda:evaluate_request(future))

    # Tamper and fork/gap tests on copies.
    tam=td/"tam";shutil.copytree(life,tam);last=sorted((tam/"authorization_events").glob("*.json"))[-1];x=load(last);x["authorization_status"]="TAMPERED";w(last,x)
    t_req=copy.deepcopy(exp);t_req["decision_id"]="JNU_SELECTION_DECISION_SYNTH_LIFE_TAMPER";t_req["decision_at_utc"]="2026-09-08T06:00:00+00:00";t_req["lifecycle_store_root"]=str(tam.resolve())
    T["primary_event_tamper_rejected"]=rejected(lambda:evaluate_request(t_req))

    back=td/"back";shutil.copytree(life,back);last=sorted((back/"authorization_events").glob("*.json"))[-1]
    bp=back/"recovery"/"backups"/"authorization_events"/last.name;bp.write_text(bp.read_text(encoding="utf-8")+" ",encoding="utf-8")
    b_req=copy.deepcopy(t_req);b_req["decision_id"]="JNU_SELECTION_DECISION_SYNTH_LIFE_BACKUP";b_req["lifecycle_store_root"]=str(back.resolve())
    T["backup_tamper_rejected"]=rejected(lambda:evaluate_request(b_req))

    gap=td/"gap";shutil.copytree(life,gap);sorted((gap/"authorization_events").glob("*.json"))[1].unlink()
    g_req=copy.deepcopy(t_req);g_req["decision_id"]="JNU_SELECTION_DECISION_SYNTH_LIFE_GAP";g_req["lifecycle_store_root"]=str(gap.resolve())
    T["sequence_gap_rejected"]=rejected(lambda:evaluate_request(g_req))

    fork=td/"fork";shutil.copytree(life,fork);src=sorted((fork/"authorization_events").glob("*.json"))[1];fx=load(src);fx["event_id"]="JNU_AUTH_EVENT_SYNTH_INT_FORK";fp=fork/"authorization_events"/"000002_JNU_AUTH_EVENT_SYNTH_INT_FORK.json";w(fp,fx)
    # give forged fork a syntactically valid backup so chain logic, not backup absence, detects the fork.
    fbp=fork/"recovery"/"backups"/"authorization_events"/fp.name;fbp.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(fp,fbp);Path(str(fbp)+".sha256").write_text(sha256_file(fbp)+"\n",encoding="utf-8")
    f_req=copy.deepcopy(t_req);f_req["decision_id"]="JNU_SELECTION_DECISION_SYNTH_LIFE_FORK";f_req["lifecycle_store_root"]=str(fork.resolve())
    T["forked_duplicate_sequence_rejected"]=rejected(lambda:evaluate_request(f_req))

    parent=td/"parent";shutil.copytree(life,parent);files=sorted((parent/"authorization_events").glob("*.json"));px=load(files[1]);px["parent_event_sha256"]="0"*64;w(files[1],px)
    # primary tamper is enough to fail backup verification first; still fail-closed.
    p_req=copy.deepcopy(t_req);p_req["decision_id"]="JNU_SELECTION_DECISION_SYNTH_LIFE_PARENT";p_req["lifecycle_store_root"]=str(parent.resolve())
    T["parent_lineage_tamper_rejected"]=rejected(lambda:evaluate_request(p_req))

    # Same integrated decision id cannot be reused with a different otherwise-valid record.
    freshlife=td/"freshlife";freshlife.mkdir();a4=make_auth("JNU_AUTH_SYNTH_INT_A4",pairs[0]);a4p=td/"a4.json";w(a4p,a4)
    i4=copy.deepcopy(issue);i4["event_id"]="JNU_AUTH_EVENT_SYNTH_INT_FRESH";i4["authorization_path"]=str(a4p.resolve());i4["authorization_sha256"]=sha256_file(a4p);i4p=td/"i4.json";w(i4p,i4);lifecycle_process(i4p,freshlife);fs=audit_chain(freshlife)
    collision=copy.deepcopy(req);collision["authorization_path"]=str(a4p.resolve());collision["authorization_sha256"]=sha256_file(a4p);collision["lifecycle_store_root"]=str(freshlife.resolve());collision["lifecycle_expected_event_count"]=1;collision["lifecycle_expected_head_sha256"]=fs["last_event_sha256"]
    cp=td/"collision.json";w(cp,collision)
    T["same_decision_id_different_record_rejected"]=rejected(lambda:process(cp,decisions))

    T["repo_internal_request_rejected"]=rejected(lambda:process(ROOT/"config/jnu_private_vendor_pair_authorization_lifecycle_checkpoint_v1.json",decisions))
    T["repo_internal_lifecycle_store_rejected"]=rejected(lambda:evaluate_request({**req,"lifecycle_store_root":str(ROOT)}))
    T["repo_internal_decision_store_rejected"]=rejected(lambda:process(qp,ROOT/"integrated-selection-store-forbidden"))

mem=load(MEMORY);key=load(KEY_CURRENT);terms=load(TERMS_CURRENT);short2=load(SHORTLIST)
T["public_real_ledger_still_zero_zero"]=mem.get("real_live_shadow_forecasts_registered")==0 and mem.get("real_live_shadow_outcomes_registered")==0
T["shortlist_still_unselected"]=short2.get("selected_market_data_provider")=="UNSELECTED" and short2.get("selected_key_custody_provider")=="UNSELECTED"
T["production_key_still_unselected_disabled"]=key.get("production_enabled") is False and key.get("vendor")=="UNSELECTED" and key.get("region")=="UNSELECTED"
T["real_provider_terms_still_unresolved"]=any(v=="UNRESOLVED" for k,v in terms.items() if k.endswith("_status"))
status="PASS" if all(T.values()) else "FAIL"
print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T)},indent=2))
raise SystemExit(0 if status=="PASS" else 1)
