from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL=ROOT/"config"/"jnu_operational_decision_protocol_v1.json"

def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,required=True)
    ap.add_argument("--output",type=Path,default=None)
    args=ap.parse_args()
    p=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    x=json.loads(args.input.read_text(encoding="utf-8"))
    byid={b["id"]:b for b in p["directional_blocks"]}
    supplied=x.get("blocks",[])
    seen=set()
    trace=[]
    bullish=0; bearish=0; eligible=0
    aligned_a={"BULLISH":0,"BEARISH":0}
    for b in supplied:
        bid=b.get("id")
        if bid not in byid: raise RuntimeError(f"unknown directional block {bid}")
        if bid in seen: raise RuntimeError(f"duplicate block {bid}")
        seen.add(bid)
        vote=b.get("vote"); quality=b.get("quality")
        if vote not in p["block_vote_enum"]: raise RuntimeError(f"invalid vote {vote} for {bid}")
        if quality not in {"A","B","C"}: raise RuntimeError(f"invalid quality {quality} for {bid}")
        reason=str(b.get("reason","")).strip()
        if not reason: raise RuntimeError(f"missing reason for {bid}")
        counts=quality in {"A","B"} and vote in {"BULLISH","BEARISH"}
        if counts:
            eligible+=1
            if vote=="BULLISH": bullish+=1
            else: bearish+=1
            if quality=="A": aligned_a[vote]+=1
        trace.append({"id":bid,"vote":vote,"quality":quality,"counts_directionally":counts,"reason":reason})
    for bid in byid:
        if bid not in seen:
            trace.append({"id":bid,"vote":"UNAVAILABLE","quality":"C","counts_directionally":False,"reason":"not supplied"})
    net=bullish-bearish
    if eligible<2 or abs(net)<2:
        bias="NEUTRAL_ABSTAIN"
    else:
        bias="BULLISH" if net>0 else "BEARISH"
    r=x.get("risk_modifiers",{})
    volatility=r.get("volatility_state","NORMAL")
    event=r.get("event_state","NORMAL")
    sq=r.get("sq_state","NORMAL")
    post_event=bool(r.get("post_event_exact_jnu_path_available",False))
    allowed_vol={"NORMAL","HIGH"}; allowed_event={"NORMAL","PRE_RELEASE_HIGH","POST_EVENT_HIGH"}; allowed_sq={"NORMAL","UNRESOLVED_HIGH"}
    if volatility not in allowed_vol: raise RuntimeError("invalid volatility_state")
    if event not in allowed_event: raise RuntimeError("invalid event_state")
    if sq not in allowed_sq: raise RuntimeError("invalid sq_state")
    forced_abstain=event=="PRE_RELEASE_HIGH" and not post_event
    if forced_abstain: bias="NEUTRAL_ABSTAIN"
    if bias=="NEUTRAL_ABSTAIN":
        confidence="LOW"
    else:
        opp="BEARISH" if bias=="BULLISH" else "BULLISH"
        medium=(abs(net)>=3 and aligned_a[bias]>=1 and aligned_a[opp]==0 and volatility!="HIGH" and sq!="UNRESOLVED_HIGH" and event!="PRE_RELEASE_HIGH" and event!="POST_EVENT_HIGH")
        confidence="MEDIUM" if medium else "LOW"
    result={
      "version":"1.0",
      "status":"OPERATIONAL_DECISION_TRACE",
      "protocol_sha256":sha(PROTOCOL),
      "bias":bias,
      "confidence":confidence,
      "eligible_directional_blocks":eligible,
      "bullish_blocks":bullish,
      "bearish_blocks":bearish,
      "net_directional_score":net,
      "quality_a_counts":aligned_a,
      "risk_modifiers":{"volatility_state":volatility,"event_state":event,"sq_state":sq,"post_event_exact_jnu_path_available":post_event},
      "event_forced_abstain":forced_abstain,
      "blocks":trace,
      "calibrated_probability":False
    }
    s=json.dumps(result,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(s+"\n",encoding="utf-8")
    print(s)
if __name__=="__main__": main()
