from __future__ import annotations
import argparse,hashlib,json
from datetime import datetime
from pathlib import Path
from jnu_private_atomic_io_v1 import require_external

ROOT=Path(__file__).resolve().parents[1]
PROTO=ROOT/"config"/"jnu_term_evidence_attestation_protocol_v1.json"
TERMS=ROOT/"config"/"jnu_provider_term_readiness_protocol_v1.json"

def load(p:Path)->dict:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict):raise RuntimeError(f"{p} must contain an object")
    return x
def sha256(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def attest(pack:dict)->dict:
    proto=load(PROTO);terms_proto=load(TERMS)
    fields=set(terms_proto["required_fields"])
    sources={}
    for s in pack.get("sources",[]):
        missing=[k for k in proto["required_source_fields"] if k not in s]
        if missing:raise RuntimeError("missing evidence source fields: "+",".join(missing))
        eid=str(s["evidence_id"])
        if eid in sources:raise RuntimeError("duplicate evidence_id: "+eid)
        if s["source_class"] not in proto["source_classes"] or s["authority"] not in proto["allowed_authorities"]:
            raise RuntimeError("invalid evidence source class/authority")
        p=Path(str(s["source_document_path"]));require_external(p,"term evidence source document")
        if not p.is_file():raise RuntimeError("term evidence source document missing")
        if sha256(p)!=str(s["document_sha256"]):raise RuntimeError("term evidence source SHA mismatch")
        sources[eid]=s
    base={"version":"1.0","evidence_as_of":pack["evidence_as_of"]}
    for k in fields:
        if k in {"version","evidence_as_of"}:continue
        if k in proto["hard_boolean_values"]:base[k]=proto["hard_boolean_values"][k]
        elif k=="service_facilitator_required":base[k]=True
        else:base[k]="UNRESOLVED"
    evidence_ledger={};seen={}
    for c in pack.get("claims",[]):
        missing=[k for k in proto["required_claim_fields"] if k not in c]
        if missing:raise RuntimeError("missing claim fields: "+",".join(missing))
        field=c["field"]
        if field not in fields:raise RuntimeError("claim targets unknown provider-term field: "+str(field))
        if c["explicitness"]!="EXPLICIT_TEXT" or c["reviewer_attestation"]!="EXPLICIT_TEXT_CONFIRMED":
            raise RuntimeError("claim is not explicitly attested")
        eids=list(c["evidence_ids"])
        if not eids or any(e not in sources for e in eids):raise RuntimeError("claim evidence reference missing")
        allowed=set(proto["authority_requirements"].get(field,[]))
        authorities={sources[e]["authority"] for e in eids}
        if allowed and not (authorities & allowed):raise RuntimeError("claim authority not allowed for field "+field)
        value=c["value"]
        if field in proto["hard_boolean_values"]:
            if value is not proto["hard_boolean_values"][field]:raise RuntimeError("hard boolean term may not be promoted to unsafe value: "+field)
        elif field=="service_facilitator_required":
            if not isinstance(value,bool):raise RuntimeError("service_facilitator_required must be boolean")
        elif value not in proto["ready_status_values"]:
            raise RuntimeError("claim value is not an explicit ready value: "+field)
        if field in seen and seen[field]!=value:raise RuntimeError("conflicting explicit claims for "+field)
        seen[field]=value;base[field]=value
        evidence_ledger[field]=[{"evidence_id":e,"authority":sources[e]["authority"],"source_class":sources[e]["source_class"],"source_uri":sources[e]["source_uri"],"document_sha256":sources[e]["document_sha256"],"locator":c["locator"]} for e in eids]
    required_ready=set(terms_proto["ready_values"])
    complete=all(base.get(k)==v for k,v in terms_proto["ready_values"].items())
    if base["service_facilitator_required"] is True:
        complete=complete and base["service_facilitator_approval_status"]=="EXPLICITLY_APPROVED"
    else:
        complete=complete and base["service_facilitator_approval_status"]=="NOT_REQUIRED"
    complete=complete and base["broker_auth_used"] is False and base["trading_permission_used"] is False and base["public_output_requested"] is False
    return {
      "version":"1.0",
      "status":"COMPLETE_EXPLICIT_TERMS" if complete else "PARTIAL_EXPLICIT_TERMS_BLOCKED",
      "evidence_as_of":pack["evidence_as_of"],
      "pack_id":pack["pack_id"],
      "provider_terms":base,
      "evidence_ledger":evidence_ledger,
      "source_count":len(sources),
      "claim_count":len(pack.get("claims",[])),
      "confidential_source_text_copied":False,
      "inferred_permission_used":False
    }

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--evidence-pack",type=Path,required=True);ap.add_argument("--output",type=Path);a=ap.parse_args()
    require_external(a.evidence_pack,"term evidence pack")
    out=attest(load(a.evidence_pack));s=json.dumps(out,ensure_ascii=False,indent=2)
    if a.output:
        require_external(a.output,"term attestation output");a.output.write_text(s+"\n",encoding="utf-8")
    print(json.dumps({"status":out["status"],"source_count":out["source_count"],"claim_count":out["claim_count"],"confidential_source_text_copied":False,"inferred_permission_used":False},indent=2))
    if out["status"]!="COMPLETE_EXPLICIT_TERMS":raise SystemExit(4)
if __name__=="__main__":main()
