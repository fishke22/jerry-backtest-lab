from __future__ import annotations
import copy, hashlib, json, shutil, tempfile
from pathlib import Path
from manage_jnu_private_vendor_pair_authorization_lifecycle_v1 import ROOT, process, audit_chain, validate_current_authorization, load, sha256_file

MEMORY=ROOT/"config"/"jnu_operational_framework_cross_session_memory_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
KEY_CURRENT=ROOT/"config"/"jnu_production_key_custody_current_v1.json"
TERMS_CURRENT=ROOT/"config"/"jnu_provider_term_readiness_current_v1.json"

def w(p:Path,x): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+"\n",encoding="utf-8")
def rejected(fn)->bool:
    try: fn();return False
    except Exception:return True

short=load(SHORTLIST);pairs=[p["id"]+"__"+k["id"] for p in short["market_data_candidates"] for k in short["key_custody_candidates"]];T={}
with tempfile.TemporaryDirectory(prefix="jnu-auth-lifecycle-") as td0:
    td=Path(td0);store=td/"store";store.mkdir()
    def auth(aid,pair,issued,valid,expires):
        return {
          "version":"1.0","artifact_class":"JNU_SYNTHETIC_USER_SELECTION_AUTHORIZATION","mode":"SYNTHETIC","synthetic_fixture":True,
          "authorization_id":aid,"authorization_scope":"VENDOR_PAIR_SELECTION","authorization_status":"SYNTHETIC_DISABLED",
          "authorizer_role":"USER_PRINCIPAL","authorizer_reference":"synthetic-user-principal-"+aid,
          "authorizer_attestation":"EXPLICIT_SYNTHETIC_AUTHORIZATION_RECORDED_DISABLED",
          "review_batch_id":"JNU_REVIEW_SYNTH_LIFECYCLE","review_receipt_sha256":hashlib.sha256(("receipt-"+aid).encode()).hexdigest(),
          "composite_dossier_sha256":hashlib.sha256(b"composite").hexdigest(),"authorized_combination_id":pair,
          "issued_at_utc":issued,"valid_from_utc":valid,"expires_at_utc":expires,
          "selection_write_permitted":False,"real_selection_authorized":False
        }
    a1=auth("JNU_AUTH_SYNTH_A1",pairs[0],"2026-09-08T01:00:00+00:00","2026-09-08T01:05:00+00:00","2026-09-20T00:00:00+00:00")
    a1p=td/"a1.json";w(a1p,a1)
    issue={
      "version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,"event_id":"JNU_AUTH_EVENT_SYNTH_001","event_type":"ISSUE","event_at_utc":"2026-09-08T02:00:00+00:00",
      "authorization_path":str(a1p.resolve()),"authorization_sha256":sha256_file(a1p),"target_authorization_id":None,
      "revocation_reason":None,"revocation_authorizer_reference":None,"revocation_authorizer_role":None,"revocation_attestation":None
    }
    ip=td/"issue.json";w(ip,issue);r1=process(ip,store);s1=audit_chain(store)
    T["issue_written"]=r1["status"]=="AUTHORIZATION_LIFECYCLE_EVENT_WRITTEN" and s1["event_count"]==1
    T["issue_sets_one_active"]=s1["active_authorization"]["authorization_id"]==a1["authorization_id"]
    T["current_a1_validates"]=validate_current_authorization(store,a1["authorization_id"],sha256_file(a1p),"2026-09-08T03:00:00+00:00")["status"]=="CURRENT_SYNTHETIC_DISABLED_AUTHORIZATION_VALIDATED"
    T["issue_replay_idempotent"]=process(ip,store)["status"]=="IDEMPOTENT_REPLAY_ACCEPTED"

    changed=copy.deepcopy(issue);changed["event_at_utc"]="2026-09-08T02:01:00+00:00";cip=td/"changed-same-event.json";w(cip,changed)
    T["same_event_id_different_request_rejected"]=rejected(lambda:process(cip,store))

    a2=auth("JNU_AUTH_SYNTH_A2",pairs[0],"2026-09-08T03:00:00+00:00","2026-09-08T03:05:00+00:00","2026-09-21T00:00:00+00:00")
    a2p=td/"a2.json";w(a2p,a2)
    sup={
      "version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,"event_id":"JNU_AUTH_EVENT_SYNTH_002","event_type":"SUPERSEDE","event_at_utc":"2026-09-08T04:00:00+00:00",
      "authorization_path":str(a2p.resolve()),"authorization_sha256":sha256_file(a2p),"target_authorization_id":a1["authorization_id"],
      "revocation_reason":None,"revocation_authorizer_reference":None,"revocation_authorizer_role":None,"revocation_attestation":None
    }
    sp=td/"sup.json";w(sp,sup);r2=process(sp,store);s2=audit_chain(store)
    T["supersede_written"]=r2["status"]=="AUTHORIZATION_LIFECYCLE_EVENT_WRITTEN" and s2["event_count"]==2
    T["supersede_sets_a2_current"]=s2["active_authorization"]["authorization_id"]==a2["authorization_id"]
    T["superseded_a1_rejected"]=rejected(lambda:validate_current_authorization(store,a1["authorization_id"],sha256_file(a1p),"2026-09-08T05:00:00+00:00"))
    T["current_a2_validates"]=validate_current_authorization(store,a2["authorization_id"],sha256_file(a2p),"2026-09-08T05:00:00+00:00")["status"]=="CURRENT_SYNTHETIC_DISABLED_AUTHORIZATION_VALIDATED"

    a3=auth("JNU_AUTH_SYNTH_A3",pairs[1],"2026-09-08T05:00:00+00:00","2026-09-08T05:05:00+00:00","2026-09-22T00:00:00+00:00")
    a3p=td/"a3.json";w(a3p,a3)
    badsup=copy.deepcopy(sup);badsup["event_id"]="JNU_AUTH_EVENT_SYNTH_PAIR_CHANGE";badsup["event_at_utc"]="2026-09-08T06:00:00+00:00";badsup["authorization_path"]=str(a3p.resolve());badsup["authorization_sha256"]=sha256_file(a3p);badsup["target_authorization_id"]=a2["authorization_id"]
    bsp=td/"badsup.json";w(bsp,badsup)
    T["silent_pair_substitution_rejected"]=rejected(lambda:process(bsp,store))

    stale_sup=copy.deepcopy(sup);stale_sup["event_id"]="JNU_AUTH_EVENT_SYNTH_STALE_SUP";stale_sup["event_at_utc"]="2026-09-08T06:00:00+00:00";stale_sup["target_authorization_id"]=a1["authorization_id"]
    ssp=td/"stale-sup.json";w(ssp,stale_sup)
    T["stale_supersede_target_rejected"]=rejected(lambda:process(ssp,store))

    issue_while_active=copy.deepcopy(issue);issue_while_active["event_id"]="JNU_AUTH_EVENT_SYNTH_ISSUE_ACTIVE";issue_while_active["event_at_utc"]="2026-09-08T06:00:00+00:00";issue_while_active["authorization_path"]=str(a3p.resolve());issue_while_active["authorization_sha256"]=sha256_file(a3p)
    iap=td/"issue-active.json";w(iap,issue_while_active)
    T["issue_while_active_rejected"]=rejected(lambda:process(iap,store))

    revoke={
      "version":"1.0","mode":"SYNTHETIC","synthetic_fixture":True,"event_id":"JNU_AUTH_EVENT_SYNTH_003","event_type":"REVOKE","event_at_utc":"2026-09-08T07:00:00+00:00",
      "authorization_path":None,"authorization_sha256":None,"target_authorization_id":a2["authorization_id"],
      "revocation_reason":"SYNTHETIC_CHANGE_CONTROL_TEST","revocation_authorizer_reference":"synthetic-user-principal-revoker",
      "revocation_authorizer_role":"USER_PRINCIPAL","revocation_attestation":"EXPLICIT_SYNTHETIC_REVOCATION_RECORDED"
    }
    rp=td/"revoke.json";w(rp,revoke);r3=process(rp,store);s3=audit_chain(store)
    T["revoke_written"]=r3["status"]=="AUTHORIZATION_LIFECYCLE_EVENT_WRITTEN" and s3["event_count"]==3
    T["revoke_clears_current"]=s3["active_authorization"] is None and s3["current_status"]=="NONE"
    T["revoked_a2_rejected"]=rejected(lambda:validate_current_authorization(store,a2["authorization_id"],sha256_file(a2p),"2026-09-08T08:00:00+00:00"))

    stale_revoke=copy.deepcopy(revoke);stale_revoke["event_id"]="JNU_AUTH_EVENT_SYNTH_STALE_REVOKE";stale_revoke["event_at_utc"]="2026-09-08T08:00:00+00:00"
    srp=td/"stale-revoke.json";w(srp,stale_revoke)
    T["revoke_when_none_rejected"]=rejected(lambda:process(srp,store))

    # Explicit pair change only after revoke then new issue.
    issue2=copy.deepcopy(issue);issue2["event_id"]="JNU_AUTH_EVENT_SYNTH_004";issue2["event_at_utc"]="2026-09-08T09:00:00+00:00";issue2["authorization_path"]=str(a3p.resolve());issue2["authorization_sha256"]=sha256_file(a3p)
    i2p=td/"issue2.json";w(i2p,issue2);process(i2p,store);s4=audit_chain(store)
    T["pair_change_after_revoke_issue_allowed"]=s4["active_authorization"]["authorization_id"]==a3["authorization_id"] and s4["active_authorization"]["authorized_combination_id"]==pairs[1]

    badrev=copy.deepcopy(revoke);badrev["event_id"]="JNU_AUTH_EVENT_SYNTH_BADREV";badrev["event_at_utc"]="2026-09-08T10:00:00+00:00";badrev["target_authorization_id"]=a3["authorization_id"];badrev["revocation_reason"]=""
    brp=td/"badrev.json";w(brp,badrev)
    T["empty_revocation_reason_rejected"]=rejected(lambda:process(brp,store))
    badrole=copy.deepcopy(badrev);badrole["event_id"]="JNU_AUTH_EVENT_SYNTH_BADROLE";badrole["revocation_reason"]="X";badrole["revocation_authorizer_role"]="OTHER";brlp=td/"badrole.json";w(brlp,badrole)
    T["wrong_revocation_role_rejected"]=rejected(lambda:process(brlp,store))
    badatt=copy.deepcopy(badrev);badatt["event_id"]="JNU_AUTH_EVENT_SYNTH_BADATT";badatt["revocation_reason"]="X";badatt["revocation_attestation"]="INFERRED";bap=td/"badatt.json";w(bap,badatt)
    T["inferred_revocation_rejected"]=rejected(lambda:process(bap,store))
    emptyref=copy.deepcopy(badrev);emptyref["event_id"]="JNU_AUTH_EVENT_SYNTH_EMPTYREF";emptyref["revocation_reason"]="X";emptyref["revocation_authorizer_reference"]="";erp=td/"emptyref.json";w(erp,emptyref)
    T["empty_revocation_authorizer_rejected"]=rejected(lambda:process(erp,store))

    # Expiry makes the current authorization unusable without mutating chain.
    T["expired_current_rejected"]=rejected(lambda:validate_current_authorization(store,a3["authorization_id"],sha256_file(a3p),"2026-09-23T00:00:00+00:00"))
    expstate=audit_chain(store,__import__("datetime").datetime.fromisoformat("2026-09-23T00:00:00+00:00"))
    T["expired_state_derived"]=expstate["current_status"]=="EXPIRED" and expstate["usable_current_authorization"] is None

    # Authorization artifact governance.
    enabled=copy.deepcopy(a3);enabled["authorization_status"]="SYNTHETIC_ENABLED";ep=td/"enabled.json";w(ep,enabled)
    badissue=copy.deepcopy(issue);badissue["event_id"]="JNU_AUTH_EVENT_SYNTH_ENABLED";badissue["event_at_utc"]="2026-09-08T10:00:00+00:00";badissue["authorization_path"]=str(ep.resolve());badissue["authorization_sha256"]=sha256_file(ep)
    # active A3 also blocks ISSUE; use a fresh store to isolate frozen-value rejection.
    fresh=td/"fresh";fresh.mkdir()
    T["enabled_authorization_rejected"]=rejected(lambda:process(Path((lambda p:(w(p,badissue),p)[1])(td/"badissue-enabled.json")),fresh))
    real=copy.deepcopy(a3);real["real_selection_authorized"]=True;realp=td/"real.json";w(realp,real);ri=copy.deepcopy(badissue);ri["event_id"]="JNU_AUTH_EVENT_SYNTH_REAL";ri["authorization_path"]=str(realp.resolve());ri["authorization_sha256"]=sha256_file(realp);rip=td/"realissue.json";w(rip,ri)
    T["real_selection_authorization_rejected"]=rejected(lambda:process(rip,fresh))
    writable=copy.deepcopy(a3);writable["selection_write_permitted"]=True;wp=td/"write.json";w(wp,writable);wi=copy.deepcopy(badissue);wi["event_id"]="JNU_AUTH_EVENT_SYNTH_WRITE";wi["authorization_path"]=str(wp.resolve());wi["authorization_sha256"]=sha256_file(wp);wip=td/"writeissue.json";w(wip,wi)
    T["selection_write_authorization_rejected"]=rejected(lambda:process(wip,fresh))
    secret=copy.deepcopy(a3);secret["api_key"]="x";sep=td/"secret.json";w(sep,secret);si=copy.deepcopy(badissue);si["event_id"]="JNU_AUTH_EVENT_SYNTH_SECRET";si["authorization_path"]=str(sep.resolve());si["authorization_sha256"]=sha256_file(sep);sip=td/"secretissue.json";w(sip,si)
    T["secret_field_rejected"]=rejected(lambda:process(sip,fresh))
    wrongsha=copy.deepcopy(issue);wrongsha["event_id"]="JNU_AUTH_EVENT_SYNTH_WRONGSHA";wrongsha["authorization_sha256"]="0"*64;wsp=td/"wrongsha.json";w(wsp,wrongsha)
    T["wrong_authorization_sha_rejected"]=rejected(lambda:process(wsp,fresh))
    missing=copy.deepcopy(issue);missing["event_id"]="JNU_AUTH_EVENT_SYNTH_MISSING";missing["authorization_path"]=str((td/"missing.json").resolve());mip=td/"missingissue.json";w(mip,missing)
    T["missing_authorization_artifact_rejected"]=rejected(lambda:process(mip,fresh))
    naive=copy.deepcopy(issue);naive["event_id"]="JNU_AUTH_EVENT_SYNTH_NAIVE";naive["event_at_utc"]="2026-09-08T02:00:00";nip=td/"naive.json";w(nip,naive)
    T["naive_event_time_rejected"]=rejected(lambda:process(nip,fresh))

    # Chain tamper/reorder/missing detection on copied stores.
    tamper=td/"tamper";shutil.copytree(store,tamper)
    f1=sorted((tamper/"authorization_events").glob("*.json"))[0];x=load(f1);x["authorization_status"]="TAMPERED";w(f1,x)
    T["event_tamper_detected"]=rejected(lambda:audit_chain(tamper))
    missingstore=td/"missingstore";shutil.copytree(store,missingstore);files=sorted((missingstore/"authorization_events").glob("*.json"));files[1].unlink()
    T["missing_event_sequence_detected"]=rejected(lambda:audit_chain(missingstore))
    parentstore=td/"parentstore";shutil.copytree(store,parentstore);files=sorted((parentstore/"authorization_events").glob("*.json"));x=load(files[1]);x["parent_event_sha256"]="0"*64;w(files[1],x)
    T["parent_hash_tamper_detected"]=rejected(lambda:audit_chain(parentstore))
    timestore=td/"timestore";shutil.copytree(store,timestore);files=sorted((timestore/"authorization_events").glob("*.json"));x=load(files[-1]);x["event_at_utc"]="2026-09-08T00:00:00+00:00";w(files[-1],x)
    T["backward_event_time_detected"]=rejected(lambda:audit_chain(timestore))

    T["repo_internal_request_rejected"]=rejected(lambda:process(ROOT/"config/jnu_private_vendor_pair_selection_authorization_checkpoint_v1.json",fresh))
    T["repo_internal_store_rejected"]=rejected(lambda:process(ip,ROOT/"auth-lifecycle-store-forbidden"))

mem=load(MEMORY);key=load(KEY_CURRENT);terms=load(TERMS_CURRENT);short2=load(SHORTLIST)
T["public_real_ledger_still_zero_zero"]=mem.get("real_live_shadow_forecasts_registered")==0 and mem.get("real_live_shadow_outcomes_registered")==0
T["shortlist_still_unselected"]=short2.get("selected_market_data_provider")=="UNSELECTED" and short2.get("selected_key_custody_provider")=="UNSELECTED"
T["production_key_still_unselected_disabled"]=key.get("production_enabled") is False and key.get("vendor")=="UNSELECTED" and key.get("region")=="UNSELECTED"
T["real_provider_terms_still_unresolved"]=any(v=="UNRESOLVED" for k,v in terms.items() if k.endswith("_status"))
status="PASS" if all(T.values()) else "FAIL"
print(json.dumps({"status":status,"tests":T,"passed":sum(T.values()),"total":len(T)},indent=2))
raise SystemExit(0 if status=="PASS" else 1)
