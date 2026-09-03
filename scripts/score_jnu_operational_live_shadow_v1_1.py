from __future__ import annotations
import argparse, hashlib, json, random, statistics, subprocess
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FD=ROOT/"live_shadow"/"forecasts"
OD=ROOT/"live_shadow"/"outcomes"
OUT=ROOT/"live_shadow"/"results"/"jnu_operational_live_shadow_current_v1_1.json"
PROTOCOL=ROOT/"config"/"jnu_operational_decision_protocol_v1.json"
FRAMEWORK=ROOT/"config"/"jnu_operational_framework_current_v1_3.json"
PREREG=ROOT/"config"/"jnu_operational_live_shadow_prereg_v1_2.json"
IMPL=ROOT/"config"/"jnu_operational_live_shadow_implementation_v1_2.json"

def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def git_run(args:list[str])->subprocess.CompletedProcess:
    return subprocess.run(["git",*args],cwd=ROOT,check=True,capture_output=True,text=True)

def enforce_tracked_clean(p:Path)->None:
    rel=p.relative_to(ROOT).as_posix()
    git_run(["ls-files","--error-unmatch",rel])
    dirty=git_run(["status","--porcelain","--",rel]).stdout.strip()
    if dirty:
        raise RuntimeError(f"real ledger file is not clean: {rel}: {dirty}")

def dt(s:str)->datetime:
    x=datetime.fromisoformat(s)
    if x.tzinfo is None: raise RuntimeError("timestamp must be offset-aware")
    return x

def recompute_trace(trace:dict, protocol:dict)->dict:
    byid={b["id"]:b for b in protocol["directional_blocks"]}
    blocks=trace.get("blocks")
    if not isinstance(blocks,list):
        raise RuntimeError("decision trace blocks missing")
    if sorted(b.get("id") for b in blocks)!=sorted(byid):
        raise RuntimeError("decision trace blocks do not match frozen block ids")
    seen=set(); bullish=0; bearish=0; eligible=0; qa={"BULLISH":0,"BEARISH":0}
    for b in blocks:
        bid=b.get("id")
        if bid in seen: raise RuntimeError(f"duplicate block in stored decision trace: {bid}")
        seen.add(bid)
        vote=b.get("vote"); quality=b.get("quality")
        if vote not in protocol["block_vote_enum"]: raise RuntimeError(f"invalid stored vote {vote}")
        if quality not in {"A","B","C"}: raise RuntimeError(f"invalid stored quality {quality}")
        counts=quality in {"A","B"} and vote in {"BULLISH","BEARISH"}
        if bool(b.get("counts_directionally"))!=counts:
            raise RuntimeError(f"counts_directionally mismatch for {bid}")
        if counts:
            eligible+=1
            if vote=="BULLISH": bullish+=1
            else: bearish+=1
            if quality=="A": qa[vote]+=1
    net=bullish-bearish
    if eligible<2 or abs(net)<2: bias="NEUTRAL_ABSTAIN"
    else: bias="BULLISH" if net>0 else "BEARISH"
    r=trace.get("risk_modifiers") or {}
    vol=r.get("volatility_state","NORMAL")
    event=r.get("event_state","NORMAL")
    sq=r.get("sq_state","NORMAL")
    post=bool(r.get("post_event_exact_jnu_path_available",False))
    if vol not in {"NORMAL","HIGH"}: raise RuntimeError("invalid stored volatility state")
    if event not in {"NORMAL","PRE_RELEASE_HIGH","POST_EVENT_HIGH"}: raise RuntimeError("invalid stored event state")
    if sq not in {"NORMAL","UNRESOLVED_HIGH"}: raise RuntimeError("invalid stored SQ state")
    force=event=="PRE_RELEASE_HIGH" and not post
    if force: bias="NEUTRAL_ABSTAIN"
    if bias=="NEUTRAL_ABSTAIN":
        conf="LOW"
    else:
        opp="BEARISH" if bias=="BULLISH" else "BULLISH"
        med=abs(net)>=3 and qa[bias]>=1 and qa[opp]==0 and vol!="HIGH" and sq!="UNRESOLVED_HIGH" and event not in {"PRE_RELEASE_HIGH","POST_EVENT_HIGH"}
        conf="MEDIUM" if med else "LOW"
    return {
        "bias":bias,"confidence":conf,"eligible_directional_blocks":eligible,
        "bullish_blocks":bullish,"bearish_blocks":bearish,"net_directional_score":net,
        "quality_a_counts":qa,"event_forced_abstain":force
    }

def bootstrap(xs,block=5,samples=5000,seed=20260903):
    if len(xs)<block: return None
    rng=random.Random(seed)
    starts=list(range(len(xs)-block+1))
    means=[]
    for _ in range(samples):
        acc=[]
        while len(acc)<len(xs):
            s=rng.choice(starts); acc.extend(xs[s:s+block])
        means.append(statistics.fmean(acc[:len(xs)]))
    means.sort()
    return {"samples":samples,"block_forecasts":block,"seed":seed,"mean":statistics.fmean(xs),
            "prob_mean_positive":sum(x>0 for x in means)/samples,
            "ci95":[means[int(.025*samples)],means[min(samples-1,int(.975*samples))]]}

def close(a,b,tol=1e-14):
    return abs(float(a)-float(b))<=tol

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--forecast-dir",type=Path,default=FD)
    ap.add_argument("--outcome-dir",type=Path,default=OD)
    ap.add_argument("--output",type=Path,default=OUT)
    ap.add_argument("--selftest-untracked",action="store_true",help="Allow custom temp dirs not tracked by Git.")
    args=ap.parse_args()

    protocol=json.loads(PROTOCOL.read_text(encoding="utf-8"))
    protocol_sha=sha(PROTOCOL)
    real=args.forecast_dir.resolve()==FD.resolve() and args.outcome_dir.resolve()==OD.resolve()
    if real and args.selftest_untracked:
        raise RuntimeError("--selftest-untracked is not allowed for the real ledger")

    forecasts={}
    forecast_paths={}
    integrity_forecasts=0
    if args.forecast_dir.exists():
        for p in sorted(args.forecast_dir.glob("*.json")):
            if real: enforce_tracked_clean(p)
            f=json.loads(p.read_text(encoding="utf-8"))
            fid=f.get("forecast_id")
            if not fid or fid!=p.stem: raise RuntimeError(f"forecast id/filename mismatch: {p}")
            if fid in forecasts: raise RuntimeError(f"duplicate forecast id {fid}")
            if f.get("exact_product") is not True: raise RuntimeError(f"forecast {fid} exact_product not true")
            if f.get("immutable_record") is not True or f.get("outcome_known_at_registration") is not False:
                raise RuntimeError(f"forecast {fid} immutable/outcome-known flags invalid")
            if f.get("framework_sha256")!=sha(FRAMEWORK): raise RuntimeError(f"forecast {fid} framework SHA mismatch")
            if f.get("shadow_prereg_sha256")!=sha(PREREG): raise RuntimeError(f"forecast {fid} prereg SHA mismatch")
            if f.get("implementation_sha256")!=sha(IMPL): raise RuntimeError(f"forecast {fid} implementation SHA mismatch")
            if f.get("decision_protocol_sha256")!=protocol_sha: raise RuntimeError(f"forecast {fid} protocol SHA mismatch")
            tr=f.get("decision_trace")
            if not isinstance(tr,dict) or tr.get("protocol_sha256")!=protocol_sha:
                raise RuntimeError(f"forecast {fid} decision trace protocol mismatch")
            if tr.get("calibrated_probability") is not False:
                raise RuntimeError(f"forecast {fid} calibrated_probability must be false")
            rc=recompute_trace(tr,protocol)
            for k in ["bias","confidence","eligible_directional_blocks","bullish_blocks","bearish_blocks","net_directional_score","event_forced_abstain"]:
                if tr.get(k)!=rc[k]: raise RuntimeError(f"forecast {fid} trace recompute mismatch: {k}")
            if tr.get("quality_a_counts")!=rc["quality_a_counts"]: raise RuntimeError(f"forecast {fid} quality-A counts mismatch")
            if f.get("bias")!=rc["bias"] or f.get("confidence")!=rc["confidence"]:
                raise RuntimeError(f"forecast {fid} top-level bias/confidence mismatch recomputed trace")
            forecasts[fid]=f; forecast_paths[fid]=p; integrity_forecasts+=1

    rows=[]; integrity_outcomes=0
    if args.outcome_dir.exists():
        for p in sorted(args.outcome_dir.glob("*.json")):
            if real: enforce_tracked_clean(p)
            o=json.loads(p.read_text(encoding="utf-8"))
            fid=o.get("forecast_id")
            if not fid or fid!=p.stem: raise RuntimeError(f"outcome id/filename mismatch: {p}")
            if fid not in forecasts: raise RuntimeError(f"outcome without forecast {fid}")
            if o.get("exact_product") is not True: raise RuntimeError(f"outcome {fid} exact_product not true")
            f=forecasts[fid]; fp=forecast_paths[fid]
            if o.get("forecast_record_sha256")!=sha(fp): raise RuntimeError(f"outcome {fid} forecast hash mismatch")
            ts=dt(o["target_close_timestamp"]); created=dt(f["created_at_taipei"])
            if ts<=created: raise RuntimeError(f"outcome {fid} timestamp not after forecast")
            if ts.date().isoformat()!=f["target_day_session_date"]: raise RuntimeError(f"outcome {fid} target date mismatch")
            ret=float(o["target_close_price"])/float(f["reference_price"])-1.0
            bias=f["bias"]
            if bias=="BULLISH": signed=ret; hit=True if ret>0 else (False if ret<0 else None)
            elif bias=="BEARISH": signed=-ret; hit=True if ret<0 else (False if ret>0 else None)
            else: signed=None; hit=None
            if not close(ret,o["outcome_return"]): raise RuntimeError(f"outcome {fid} return mismatch")
            if signed is None:
                if o.get("signed_outcome_return") is not None: raise RuntimeError(f"outcome {fid} signed return should be null")
            elif not close(signed,o["signed_outcome_return"]): raise RuntimeError(f"outcome {fid} signed return mismatch")
            if o.get("directional_hit")!=hit: raise RuntimeError(f"outcome {fid} hit mismatch")
            rows.append({"forecast_id":fid,"bias":bias,"confidence":f["confidence"],
                         "outcome_return":ret,"directional_hit":hit,"signed_outcome_return":signed})
            integrity_outcomes+=1

    scored=[r for r in rows if r["bias"]!="NEUTRAL_ABSTAIN"]
    signed=[float(r["signed_outcome_return"]) for r in scored]
    hits=[r["directional_hit"] for r in scored if r["directional_hit"] is not None]
    by_conf={}
    for c in ["LOW","MEDIUM"]:
        rr=[r for r in scored if r["confidence"]==c]
        hh=[r["directional_hit"] for r in rr if r["directional_hit"] is not None]
        ss=[float(r["signed_outcome_return"]) for r in rr]
        by_conf[c]={"n":len(rr),"accuracy":sum(bool(x) for x in hh)/len(hh) if hh else None,
                    "mean_signed_return":statistics.fmean(ss) if ss else None}
    b=bootstrap(signed) if signed else None
    n=len(scored)
    accuracy=sum(bool(x) for x in hits)/len(hits) if hits else None
    gate={
      "minimum_30_nonabstain":n>=30,
      "directional_accuracy_gt_0_50":accuracy>0.5 if accuracy is not None else False,
      "mean_signed_return_positive":statistics.fmean(signed)>0 if signed else False,
      "bootstrap_prob_mean_positive_ge_0_90":b is not None and b["prob_mean_positive"]>=0.90
    }
    status="LIVE_SHADOW_FIRST_REVIEW_PASS" if n>=30 and all(gate.values()) else ("LIVE_SHADOW_FIRST_REVIEW_FAIL" if n>=30 else "LIVE_SHADOW_ACCUMULATING")
    result={
      "version":"1.1","status":status,
      "integrity":{"status":"PASS","forecasts_verified":integrity_forecasts,"outcomes_verified":integrity_outcomes,
                   "git_tracking_enforced":real,"decision_trace_recomputed":True,"outcomes_recomputed":True,
                   "protocol_sha256":protocol_sha},
      "framework_sha256":sha(FRAMEWORK),"prereg_sha256":sha(PREREG),"implementation_sha256":sha(IMPL),
      "forecast_records":len(forecasts),"outcomes_recorded":len(rows),
      "nonabstain_scored":n,"abstain_with_outcome":sum(r["bias"]=="NEUTRAL_ABSTAIN" for r in rows),
      "coverage":n/len(rows) if rows else None,"directional_accuracy":accuracy,
      "mean_signed_return":statistics.fmean(signed) if signed else None,
      "median_signed_return":statistics.median(signed) if signed else None,
      "by_confidence":by_conf,"bootstrap":b,"first_review_gate":gate,"rows":rows
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="rows"},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
