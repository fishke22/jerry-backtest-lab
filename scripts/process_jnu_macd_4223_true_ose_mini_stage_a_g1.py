from __future__ import annotations
import csv,hashlib,json,random,statistics
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PREREG=ROOT/"config"/"jnu_macd_4223_post_publication_true_jnu_g1_prereg.json"
PANEL=ROOT/"cloud_data"/"derived"/"jnu_macd_4223_mini_stage_a_g1.csv"
MANIFEST=ROOT/"cloud_data"/"manifests"/"jnu_macd_4223_mini_stage_a_g1_manifest.json"
RESULT=ROOT/"directional_results"/"jnu_macd_4223_true_ose_mini_stage_a_g1.json"
REPORT=ROOT/"directional_reports"/"jnu_macd_4223_true_ose_mini_stage_a_g1.md"

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for b in iter(lambda:fh.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def q(xs,q):
    ys=sorted(xs); pos=(len(ys)-1)*q; lo=int(pos); hi=min(lo+1,len(ys)-1); f=pos-lo
    return ys[lo]*(1-f)+ys[hi]*f

def bootstrap(xs,n,seed):
    rng=random.Random(seed); m=len(xs); means=[]
    for _ in range(n):
        means.append(sum(xs[rng.randrange(m)] for _ in range(m))/m)
    p=sum(x>0 for x in means)/n
    return {"samples":n,"seed":seed,"prob_mean_positive":p,"one_sided_p":1-p,"ci95":[q(means,.025),q(means,.975)]}

def main():
    pre=json.loads(PREREG.read_text(encoding="utf-8"))
    man=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if man.get("raw_data_cloud_uploaded") is not False: raise RuntimeError("raw cloud")
    if man.get("critical_data_quality_issues"): raise RuntimeError("critical DQ")
    if man.get("derived_output_hash")!=sha256_file(PANEL): raise RuntimeError("hash mismatch")
    if man.get("stage")!="A_TRUE_OSE_MINI": raise RuntimeError("wrong stage")
    if man.get("market_outcome_interpretation_performed") is not False: raise RuntimeError("local interpretation")
    rows=list(csv.DictReader(PANEL.open(encoding="utf-8")))
    payoff=[float(r["signal_payoff"]) for r in rows]
    correct=sum(int(r["correct"]) for r in rows)
    denom=sum(int(r["accuracy_denominator"]) for r in rows)
    acc=correct/denom if denom else None
    mean_pay=statistics.fmean(payoff) if payoff else None
    b=pre["inference"]["bootstrap"]
    bs=bootstrap(payoff,int(b["resamples"]),int(b["seed"]))
    passed=bool(len(rows)>=200 and mean_pay is not None and mean_pay>0 and acc is not None and acc>0.5 and bs["prob_mean_positive"]>=0.95)
    status="TRUE_OSE_MINI_MACD4223_STAGE_A_PASS" if passed else "TRUE_OSE_MINI_MACD4223_STAGE_A_FAIL"
    result={
      "candidate_id":pre["candidate_id"],"stage":"A_TRUE_OSE_MINI","status":status,"stage_a_pass":passed,
      "role":"DIRECTIONAL_INFORMATION_GATE","usable_days":len(rows),"minimum_usable_days":200,
      "mean_daily_signal_payoff":mean_pay,"aggregate_directional_accuracy_nonzero_targets":acc,
      "bootstrap":bs,"derived_panel_sha256":sha256_file(PANEL),"manifest_sha256":sha256_file(MANIFEST),
      "next_rule":"Proceed to exact JNU Micro Stage B without retuning." if passed else "Close family; no MACD parameter re-optimization or filter rescue.",
      "generated_at_utc":datetime.now(timezone.utc).isoformat()
    }
    RESULT.parent.mkdir(parents=True,exist_ok=True); REPORT.parent.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(
      "# Post-publication MACD(4,22,3) true-OSE Mini Stage A\n\n"
      f"- Status: **{status}**\n- Usable days: {len(rows)}\n- Mean signal payoff: {mean_pay}\n"
      f"- Directional accuracy: {acc}\n- Bootstrap P(mean>0): {bs['prob_mean_positive']}\n",
      encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
