from __future__ import annotations
import csv,hashlib,json,math,random,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ALIGN=ROOT/"flow_results"/"jnu_jpx_cash_foreign_flow_alignment_v1.json"
PREREG=ROOT/"config"/"jnu_jpx_cash_foreign_flow_tokyo_nagoya_sign_g1_prereg.json"
FRED=Path(r"D:\Temp\nikkei225_2016_20260902.csv")
OUT=Path(r"D:\Temp\jnu_jpx_cash_foreign_flow_phase1_result.json")
REPORT=Path(r"D:\Temp\jnu_jpx_cash_foreign_flow_phase1_report.md")

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def cum(xs):
    z=1.0
    for x in xs: z*=1+x
    return z-1
def shp(xs):
    return statistics.fmean(xs)/statistics.stdev(xs)*math.sqrt(52.0)
def boot(xs,block=5,samples=5000,seed=42):
    rng=random.Random(seed); starts=list(range(len(xs)-block+1)); means=[]
    for _ in range(samples):
        acc=[]
        while len(acc)<len(xs):
            s=rng.choice(starts); acc.extend(xs[s:s+block])
        means.append(statistics.fmean(acc[:len(xs)]))
    means.sort()
    return {
        "samples":samples,"block_weeks":block,"seed":seed,
        "mean":statistics.fmean(xs),
        "prob_mean_positive":sum(m>0 for m in means)/samples,
        "lower_2_5pct":means[int(0.025*samples)],
        "lower_1_25pct":means[int(0.0125*samples)],
        "upper_97_5pct":means[min(samples-1,int(0.975*samples))]
    }
def main():
    a=json.loads(ALIGN.read_text(encoding="utf-8"))
    pre=json.loads(PREREG.read_text(encoding="utf-8"))
    if a["status"]!="ALIGNMENT_FROZEN_BEFORE_PRICE_VALUE_READ" or a["directional_outcome_inspected"] is not False: raise RuntimeError("alignment guard")
    if pre["directional_outcome_inspected"] is not False: raise RuntimeError("prereg guard")
    px={}
    with FRED.open(encoding="utf-8",newline="") as f:
        for r in csv.DictReader(f):
            v=(r.get("NIKKEI225") or "").strip()
            if v not in {"",".","NA","NaN"}: px[r["observation_date"]]=float(v)
    rows=[]; prev=0
    for x in a["records"]:
        pos=int(x["foreign_flow_sign"]); u=px[x["exit_date"]]/px[x["entry_date"]]-1
        turnover=abs(pos-prev); gross=pos*u
        n10=gross-turnover*0.001; n20=gross-turnover*0.002
        rows.append({**x,"position":pos,"turnover":turnover,"underlying_return":u,"strategy_gross_return":gross,"net_return_10bps":n10,"net_return_20bps":n20})
        prev=pos
    n10=[r["net_return_10bps"] for r in rows]; n20=[r["net_return_20bps"] for r in rows]
    b=boot(n10)
    subs=[]
    for k in range(1,5):
        rr=[r for r in rows if r["subperiod"]==k]
        subs.append({"subperiod":k,"n":len(rr),"from":rr[0]["publication_date"],"to":rr[-1]["publication_date"],"net_cumulative_10bps":cum([r["net_return_10bps"] for r in rr]),"net_cumulative_20bps":cum([r["net_return_20bps"] for r in rr])})
    pos_sub=sum(s["net_cumulative_10bps"]>0 for s in subs)
    metrics={
        "net_cumulative_10bps":cum(n10),
        "net_cumulative_20bps":cum(n20),
        "mean_weekly_net_10bps":statistics.fmean(n10),
        "annualized_sharpe_10bps":shp(n10),
        "bootstrap":b,
        "positive_subperiods":int(pos_sub),
        "recent_104_net_cumulative_10bps":cum(n10[-104:])
    }
    checks={
        "minimum_300_observations":len(rows)>=300,
        "net_cumulative_10bps_positive":metrics["net_cumulative_10bps"]>0,
        "annualized_sharpe_positive":metrics["annualized_sharpe_10bps"]>0,
        "stress_20bps_cumulative_positive":metrics["net_cumulative_20bps"]>0,
        "bootstrap_standard_lower_2_5pct_positive":b["lower_2_5pct"]>0,
        "bootstrap_bonferroni_lower_1_25pct_positive":b["lower_1_25pct"]>0,
        "at_least_3_of_4_subperiods_positive":pos_sub>=3
    }
    passed=all(checks.values())
    status="HISTORICAL_OOS_PASS_PROXY_REQUIRES_TRUE_JNU_CONFIRMATION" if passed else "JPX_CASH_FOREIGN_FLOW_PHASE1_FAIL_TERMINAL_CURRENT_SPEC"
    out={
        "version":"1.0","candidate_id":"JPX_CASH_FOREIGN_FLOW_TOKYO_NAGOYA_SIGN_G1",
        "status":status,"phase1_pass":passed,"validated_jnu_module":False,"validated_directional_edge":False,
        "alignment_sha256":sha(ALIGN),"prereg_sha256":sha(PREREG),"fred_csv_sha256":sha(FRED),
        "observations":len(rows),
        "positions":{"long":sum(r["position"]==1 for r in rows),"short":sum(r["position"]==-1 for r in rows),"flat":sum(r["position"]==0 for r in rows)},
        "metrics":metrics,"subperiods":subs,"checks":checks,"records":rows
    }
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    REPORT.write_text("\n".join([
        "# JPX Cash Foreign Flow Tokyo & Nagoya Sign G1 - Phase1","",
        f"- Status: **{status}**",f"- Observations: **{len(rows)}**",
        f"- 10bps cumulative: **{metrics['net_cumulative_10bps']:.6%}**",
        f"- 20bps cumulative: **{metrics['net_cumulative_20bps']:.6%}**",
        f"- Sharpe: **{metrics['annualized_sharpe_10bps']}**",
        f"- Bootstrap lower 2.5%: **{b['lower_2_5pct']:.8f}**",
        f"- Bonferroni lower 1.25%: **{b['lower_1_25pct']:.8f}**",
        f"- Positive subperiods: **{pos_sub}/4**",
        f"- Recent 104 cumulative: **{metrics['recent_104_net_cumulative_10bps']:.6%}**"
    ])+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in out.items() if k!="records"},indent=2,ensure_ascii=False))
if __name__=="__main__": main()
