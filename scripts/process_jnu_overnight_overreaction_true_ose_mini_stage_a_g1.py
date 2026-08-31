from __future__ import annotations
import csv,hashlib,json,random,statistics
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PREREG=ROOT/"config"/"jnu_overnight_overreaction_true_jnu_g1_prereg.json"
PANEL=ROOT/"cloud_data"/"derived"/"jnu_overnight_overreaction_mini_stage_a_g1.csv"
MANIFEST=ROOT/"cloud_data"/"manifests"/"jnu_overnight_overreaction_mini_stage_a_g1_manifest.json"
RESULT=ROOT/"directional_results"/"jnu_overnight_overreaction_true_ose_mini_stage_a_g1.json"
REPORT=ROOT/"directional_reports"/"jnu_overnight_overreaction_true_ose_mini_stage_a_g1.md"

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for b in iter(lambda:fh.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def quantile_sorted(xs,q):
    ys=sorted(xs); pos=(len(ys)-1)*q; lo=int(pos); hi=min(lo+1,len(ys)-1); f=pos-lo
    return ys[lo]*(1-f)+ys[hi]*f

def bootstrap(xs,samples,seed):
    rng=random.Random(seed); n=len(xs); means=[]
    for _ in range(samples):
        means.append(sum(xs[rng.randrange(n)] for _ in range(n))/n)
    p=sum(m>0 for m in means)/samples
    return {"samples":samples,"seed":seed,"prob_mean_positive":p,"one_sided_p":1-p,"ci95":[quantile_sorted(means,.025),quantile_sorted(means,.975)]}

def ols_slope(xs,ys):
    mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
    den=sum((x-mx)**2 for x in xs)
    return None if den==0 else sum((x-mx)*(y-my) for x,y in zip(xs,ys))/den

def main():
    pre=json.loads(PREREG.read_text(encoding="utf-8"))
    m=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if m.get("raw_data_cloud_uploaded") is not False: raise RuntimeError("raw cloud")
    if m.get("critical_data_quality_issues"): raise RuntimeError("critical DQ")
    if m.get("derived_output_hash")!=sha256_file(PANEL): raise RuntimeError("hash mismatch")
    if m.get("stage")!="A_TRUE_OSE_MINI": raise RuntimeError("wrong stage")
    if m.get("market_outcome_interpretation_performed") is not False: raise RuntimeError("local interpretation")
    rows=list(csv.DictReader(PANEL.open(encoding="utf-8")))
    payoff=[float(r["signal_payoff"]) for r in rows]
    overnight=[float(r["overnight_return"]) for r in rows]
    morning=[float(r["morning_return"]) for r in rows]
    correct=sum(int(r["correct"]) for r in rows)
    denom=sum(int(r["accuracy_denominator"]) for r in rows)
    acc=correct/denom if denom else None
    mean_pay=statistics.fmean(payoff) if payoff else None
    bcfg=pre["inference"]["bootstrap"]
    bs=bootstrap(payoff,int(bcfg["resamples"]),int(bcfg["seed"]))
    passed=bool(len(rows)>=1000 and mean_pay is not None and mean_pay>0 and acc is not None and acc>0.5 and bs["prob_mean_positive"]>=0.95)
    status="TRUE_OSE_MINI_OVERNIGHT_OVERREACTION_STAGE_A_PASS" if passed else "TRUE_OSE_MINI_OVERNIGHT_OVERREACTION_STAGE_A_FAIL"
    result={
      "candidate_id":pre["candidate_id"],"stage":"A_TRUE_OSE_MINI","status":status,"stage_a_pass":passed,
      "role":"DIRECTIONAL_INFORMATION_GATE","usable_days":len(rows),"minimum_usable_days":1000,
      "mean_daily_signal_payoff":mean_pay,"aggregate_directional_accuracy_nonzero_targets":acc,
      "correct_nonzero_targets":correct,"accuracy_denominator":denom,"bootstrap":bs,
      "diagnostic_ols_slope_morning_on_overnight":ols_slope(overnight,morning),
      "derived_panel_sha256":sha256_file(PANEL),"manifest_sha256":sha256_file(MANIFEST),
      "next_rule":"Proceed to exact JNU Micro Stage B with no retuning." if passed else "Close family; no horizon/filter/sign/night-session rescue and no Micro rescue.",
      "generated_at_utc":datetime.now(timezone.utc).isoformat()
    }
    RESULT.parent.mkdir(parents=True,exist_ok=True); REPORT.parent.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(
      "# True-OSE Mini overnight-overreaction Stage A G1\n\n"
      f"- Status: **{status}**\n- Usable days: {len(rows)}\n- Mean signal payoff: {mean_pay}\n"
      f"- Directional accuracy: {acc}\n- Bootstrap P(mean>0): {bs['prob_mean_positive']}\n"
      f"- Diagnostic slope morning~overnight: {result['diagnostic_ols_slope_morning_on_overnight']}\n",
      encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
