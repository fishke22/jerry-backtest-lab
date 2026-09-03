from __future__ import annotations
import argparse, json, random, statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FD=ROOT/"live_shadow"/"forecasts"
OD=ROOT/"live_shadow"/"outcomes"
OUT=ROOT/"live_shadow"/"results"/"jnu_operational_live_shadow_current_v1.json"

def bootstrap(xs,block=5,samples=5000,seed=20260903):
    if len(xs)<block: return None
    rng=random.Random(seed); starts=list(range(len(xs)-block+1)); means=[]
    for _ in range(samples):
        acc=[]
        while len(acc)<len(xs):
            s=rng.choice(starts); acc.extend(xs[s:s+block])
        means.append(statistics.fmean(acc[:len(xs)]))
    means.sort()
    return {"samples":samples,"block_forecasts":block,"seed":seed,"mean":statistics.fmean(xs),
            "prob_mean_positive":sum(x>0 for x in means)/samples,
            "ci95":[means[int(.025*samples)],means[min(samples-1,int(.975*samples))]]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--forecast-dir",type=Path,default=FD)
    ap.add_argument("--outcome-dir",type=Path,default=OD)
    ap.add_argument("--output",type=Path,default=OUT)
    args=ap.parse_args()
    forecasts={}
    if args.forecast_dir.exists():
        for p in sorted(args.forecast_dir.glob("*.json")):
            f=json.loads(p.read_text(encoding="utf-8")); forecasts[f["forecast_id"]]=f
    rows=[]
    if args.outcome_dir.exists():
        for p in sorted(args.outcome_dir.glob("*.json")):
            o=json.loads(p.read_text(encoding="utf-8")); fid=o["forecast_id"]
            if fid not in forecasts: raise RuntimeError(f"outcome without forecast {fid}")
            f=forecasts[fid]
            rows.append({"forecast_id":fid,"bias":f["bias"],"confidence":f["confidence"],
                         "outcome_return":o["outcome_return"],"directional_hit":o["directional_hit"],
                         "signed_outcome_return":o["signed_outcome_return"]})
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
    result={"version":"1.0","status":status,"forecast_records":len(forecasts),"outcomes_recorded":len(rows),
            "nonabstain_scored":n,"abstain_with_outcome":sum(r["bias"]=="NEUTRAL_ABSTAIN" for r in rows),
            "coverage":n/len(rows) if rows else None,"directional_accuracy":accuracy,
            "mean_signed_return":statistics.fmean(signed) if signed else None,
            "median_signed_return":statistics.median(signed) if signed else None,
            "by_confidence":by_conf,"bootstrap":b,"first_review_gate":gate,"rows":rows}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="rows"},ensure_ascii=False,indent=2))
if __name__=="__main__": main()
