from __future__ import annotations
import argparse, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"config"/"jnu_provider_evidence_intake_protocol_v1.json"
SHORTLIST=ROOT/"config"/"jnu_provider_selection_shortlist_v1.json"
TEMPLATES=ROOT/"config"/"jnu_provider_evidence_intake_pack_templates_v1.json"
DANGEROUS={"api_key","access_token","password","secret","client_secret","private_key","material_b64","token"}

def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise RuntimeError(f"{p} must contain an object")
    return x

def secret_keys(x,path="root"):
    hits=[]
    if isinstance(x,dict):
        for k,v in x.items():
            if str(k).lower() in DANGEROUS: hits.append(path+"."+str(k))
            hits.extend(secret_keys(v,path+"."+str(k)))
    elif isinstance(x,list):
        for i,v in enumerate(x): hits.extend(secret_keys(v,f"{path}[{i}]"))
    return hits

def validate(protocol:dict,shortlist:dict,templates:dict)->dict:
    g=protocol.get("governance") or {}
    if g.get("synthetic_only") is not True: raise RuntimeError("intake protocol must remain synthetic-only")
    for k in ["outreach_authorized","vendor_selection_permitted","credential_collection_permitted","real_entitled_data_permitted","public_repo_source_document_storage_permitted","real_activation_manifest_generation_prohibited_in_this_stage"]:
        want=False if k!="real_activation_manifest_generation_prohibited_in_this_stage" else True
        if g.get(k) is not want: raise RuntimeError("governance flag invalid: "+k)
    if shortlist.get("selected_market_data_provider")!="UNSELECTED" or shortlist.get("selected_key_custody_provider")!="UNSELECTED":
        raise RuntimeError("shortlist unexpectedly performs selection")
    if templates.get("selected_market_data_provider")!="UNSELECTED" or templates.get("selected_key_custody_provider")!="UNSELECTED":
        raise RuntimeError("intake templates may not perform provider selection")
    if templates.get("real_activation_manifest_generated") is not False:
        raise RuntimeError("intake stage may not generate real activation manifest")
    hits=secret_keys(templates)
    if hits: raise RuntimeError("secret-like key prohibited in public intake template: "+hits[0])

    md_short={x["id"]:x for x in shortlist["market_data_candidates"]}
    md_packs={x["candidate_id"]:x for x in templates.get("market_data_provider_packs",[])}
    if set(md_packs)!=set(md_short): raise RuntimeError("market-data candidate coverage mismatch")
    required_md=set(protocol["market_data_required_target_fields"])
    for cid,p in md_packs.items():
        if p.get("outreach_authorized") is not False or p.get("contact_status")!="UNCONTACTED_DRAFT_UNSENT":
            raise RuntimeError("market-data outreach must remain unsent: "+cid)
        if p.get("provider_selected") is not False: raise RuntimeError("market-data pack may not select provider: "+cid)
        if p.get("legal_or_brand_name")!=md_short[cid].get("legal_or_brand_name"):
            raise RuntimeError("market-data identity mismatch: "+cid)
        qs=p.get("questionnaire") or []
        targets={q.get("target_field") for q in qs}
        if not required_md.issubset(targets): raise RuntimeError("market-data required questions missing: "+cid)
        for q in qs:
            if not all(q.get(k) for k in ["id","target_field","prompt","evidence_requested"]):
                raise RuntimeError("market-data questionnaire field missing: "+cid)
            if q.get("status")!="UNRESOLVED": raise RuntimeError("market-data question pre-resolved: "+cid)

    ose=templates.get("ose_authority_pack") or {}
    if ose.get("authority")!="OSE" or ose.get("outreach_authorized") is not False or ose.get("contact_status")!="UNCONTACTED_DRAFT_UNSENT":
        raise RuntimeError("OSE intake pack must remain draft unsent")
    if not set(protocol["ose_required_target_fields"]).issubset({q.get("target_field") for q in ose.get("questionnaire",[])}):
        raise RuntimeError("OSE required questions missing")
    if any(q.get("status")!="UNRESOLVED" for q in ose.get("questionnaire",[])):
        raise RuntimeError("OSE question pre-resolved")

    kms_short={x["id"]:x for x in shortlist["key_custody_candidates"]}
    kms_packs={x["candidate_id"]:x for x in templates.get("key_custody_deployment_packs",[])}
    if set(kms_packs)!=set(kms_short): raise RuntimeError("KMS candidate coverage mismatch")
    required_kms=set(protocol["kms_required_deployment_fields"])
    for cid,p in kms_packs.items():
        if p.get("provider_selected") is not False or p.get("deployment_profile_status")!="DRAFT_UNATTESTED":
            raise RuntimeError("KMS deployment profile must remain unselected/unattested: "+cid)
        if p.get("vendor")!=kms_short[cid].get("vendor") or p.get("proposed_region")!=kms_short[cid].get("proposed_region"):
            raise RuntimeError("KMS identity/region mismatch: "+cid)
        rows=p.get("deployment_attestation") or []
        fields={r.get("field") for r in rows}
        if fields!=required_kms: raise RuntimeError("KMS deployment attestation field coverage mismatch: "+cid)
        if any(r.get("status") not in protocol["allowed_attestation_statuses"] for r in rows):
            raise RuntimeError("KMS deployment attestation prematurely resolved: "+cid)
        if any(r.get("attestation_value") is not None or r.get("reviewer_attestation") is not None for r in rows):
            raise RuntimeError("KMS deployment attestation contains unapproved production assertions: "+cid)

    return {
      "version":"1.0",
      "status":"PASS_DRAFT_PACK_READY_UNSENT",
      "market_data_candidates_covered":len(md_packs),
      "key_custody_candidates_covered":len(kms_packs),
      "ose_authority_pack":True,
      "outreach_sent":False,
      "provider_selection_performed":False,
      "real_activation_manifest_generated":False,
      "secret_like_keys_found":0
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--protocol",type=Path,default=PROTOCOL)
    ap.add_argument("--shortlist",type=Path,default=SHORTLIST)
    ap.add_argument("--templates",type=Path,default=TEMPLATES)
    a=ap.parse_args()
    print(json.dumps(validate(load(a.protocol),load(a.shortlist),load(a.templates)),indent=2))

if __name__=="__main__": main()
