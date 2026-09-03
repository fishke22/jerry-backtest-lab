from __future__ import annotations
import csv, hashlib, json, math, random, statistics
from pathlib import Path

ROOT=Path(r"D:\JERRY_BACKTEST_CLOUD_SYNC_20260831")
CSV=Path(r"D:\Temp\nikkei225_2014_20260831.csv")
ALIGN=ROOT/"config"/"jnu_dekansho_bushi_postpublication_alignment_v1.json"
PREREG=ROOT/"config"/"jnu_dekansho_bushi_postpublication_g1_prereg.json"
COST=ROOT/"config"/"jnu_dekansho_bushi_cost_alignment_clarification_v1.json"
OUT=Path(r"D:\Temp\jnu_dekansho_bushi_postpublication_phase0_result.json")
REPORT=Path(r"D:\Temp\jnu_dekansho_bushi_postpublication_phase0_report.md")

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def cumulative(xs:list[float])->float:
    z=1.0
    for x in xs: z*=1.0+x
    return z-1.0

def sharpe_monthly(xs:list[float])->float|None:
    if len(xs)<2: return None
    sd=statistics.stdev(xs)
    if sd==0: return None
    return statistics.fmean(xs)/sd*math.sqrt(12.0)

def moving_block_bootstrap(xs:list[float],block:int=6,samples:int=10000,seed:int=42)->dict:
    n=len(xs)
    if n<block: raise RuntimeError("sample shorter than block")
    rng=random.Random(seed)
    starts=list(range(n-block+1))
    means=[]
    for _ in range(samples):
        acc=[]
        while len(acc)<n:
            s=rng.choice(starts)
            acc.extend(xs[s:s+block])
        means.append(statistics.fmean(acc[:n]))
    means.sort()
    return {
        "samples":samples,
        "block_months":block,
        "seed":seed,
        "mean":statistics.fmean(xs),
        "prob_mean_positive":sum(x>0 for x in means)/samples,
        "ci95":[means[int(0.025*samples)],means[min(samples-1,int(0.975*samples))]],
        "lower_95":means[int(0.025*samples)]
    }

def main():
    align=json.loads(ALIGN.read_text(encoding="utf-8"))
    pre=json.loads(PREREG.read_text(encoding="utf-8"))
    cost=json.loads(COST.read_text(encoding="utf-8"))
    if align.get("status")!="ALIGNMENT_FROZEN_BEFORE_PRICE_VALUE_READ": raise RuntimeError("alignment not frozen")
    if align.get("price_values_parsed") is not False: raise RuntimeError("alignment outcome guard")
    if pre.get("directional_outcome_inspected") is not False: raise RuntimeError("prereg outcome guard")
    if cost.get("directional_outcome_inspected") is not False: raise RuntimeError("cost outcome guard")
    if sha(CSV)!=align["fred_csv_sha256"]: raise RuntimeError("FRED CSV hash mismatch")

    px={}
    with CSV.open(encoding="utf-8",newline="") as f:
        for r in csv.DictReader(f):
            v=(r.get("NIKKEI225") or "").strip()
            if v in {"",".","NA","NaN"}: continue
            px[r["observation_date"]]=float(v)

    daily=[]
    for a in align["daily_alignment"]:
        d=a["return_date"]; prev=a["prior_valid_close_date"]
        if d not in px or prev not in px: raise RuntimeError(f"missing price {prev}->{d}")
        underlying=px[d]/px[prev]-1.0
        pos=int(a["position"])
        gross=pos*underlying
        units=int(a["transition_cost_units"])
        net10=gross-units*0.001
        net20=gross-units*0.002
        daily.append({
            **a,
            "prior_close":px[prev],
            "close":px[d],
            "underlying_return":underlying,
            "gross_strategy_return":gross,
            "net_return_10bps":net10,
            "net_return_20bps":net20
        })

    months=[]
    for m in align["monthly_alignment"]:
        rr=[r for r in daily if r["month"]==m["month"]]
        if not rr: raise RuntimeError(f"no daily returns for {m['month']}")
        months.append({
            **m,
            "net_monthly_return_10bps":cumulative([r["net_return_10bps"] for r in rr]),
            "net_monthly_return_20bps":cumulative([r["net_return_20bps"] for r in rr]),
            "gross_monthly_return":cumulative([r["gross_strategy_return"] for r in rr])
        })

    primary=[m["net_monthly_return_10bps"] for m in months]
    stress=[m["net_monthly_return_20bps"] for m in months]
    boot=moving_block_bootstrap(primary)
    shp=sharpe_monthly(primary)
    subs=[]
    for b in range(1,5):
        mm=[m for m in months if m["subperiod"]==b]
        subs.append({
            "subperiod":b,
            "n_months":len(mm),
            "from":mm[0]["month"],
            "to":mm[-1]["month"],
            "net_cumulative_10bps":cumulative([m["net_monthly_return_10bps"] for m in mm]),
            "net_cumulative_20bps":cumulative([m["net_monthly_return_20bps"] for m in mm]),
            "mean_monthly_net_10bps":statistics.fmean([m["net_monthly_return_10bps"] for m in mm])
        })
    pos_sub=sum(x["net_cumulative_10bps"]>0 for x in subs)
    recent=months[-36:]
    metrics={
        "net_cumulative_10bps":cumulative(primary),
        "net_cumulative_20bps":cumulative(stress),
        "mean_monthly_net_10bps":statistics.fmean(primary),
        "annualized_monthly_sharpe_10bps":shp,
        "bootstrap":boot,
        "positive_subperiods":pos_sub,
        "recent_36_month_net_cumulative_10bps":cumulative([m["net_monthly_return_10bps"] for m in recent])
    }
    checks={
        "minimum_144_complete_months":len(months)>=144,
        "net_cumulative_10bps_positive":metrics["net_cumulative_10bps"]>0,
        "annualized_monthly_sharpe_positive":(shp is not None and shp>0),
        "stress_20bps_cumulative_positive":metrics["net_cumulative_20bps"]>0,
        "bootstrap_95_lower_mean_positive":boot["lower_95"]>0,
        "at_least_3_of_4_subperiods_positive":pos_sub>=3
    }
    passed=all(checks.values())
    status="POSTPUBLICATION_SPOT_REPLICATION_PASS_REQUIRES_TRUE_OSE_CONFIRMATION" if passed else "DEKANSHO_BUSHI_POSTPUBLICATION_FAIL_CURRENT_SPEC"
    out={
        "version":"1.0",
        "candidate_id":"NIKKEI_DEKANSHO_BUSHI_POSTPUBLICATION_G1",
        "status":status,
        "phase0_pass":passed,
        "validated_jnu_module":False,
        "validated_directional_edge":False,
        "prereg_sha256":sha(PREREG),
        "cost_clarification_sha256":sha(COST),
        "alignment_sha256":sha(ALIGN),
        "fred_csv_sha256":sha(CSV),
        "sample":{"from":"2014-01","to":"2026-08","months":len(months),"daily_returns":len(daily)},
        "positions":{"long_months":sum(m["position"]==1 for m in months),"short_months":sum(m["position"]==-1 for m in months)},
        "metrics":metrics,
        "subperiods":subs,
        "checks":checks,
        "monthly_records":months,
        "daily_records":daily
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text("\n".join([
        "# Nikkei Dekansho-bushi Postpublication G1 - Phase0","",
        f"- Status: **{status}**",
        f"- Sample: **2014-01 through 2026-08; {len(months)} months**",
        f"- Long / Short months: **{out['positions']['long_months']} / {out['positions']['short_months']}**",
        f"- Net cumulative 10bps: **{metrics['net_cumulative_10bps']:.6%}**",
        f"- Net cumulative 20bps: **{metrics['net_cumulative_20bps']:.6%}**",
        f"- Annualized monthly Sharpe: **{shp}**",
        f"- Bootstrap lower 95% mean monthly net: **{boot['lower_95']:.8f}**",
        f"- Positive subperiods: **{pos_sub}/4**",
        f"- Recent 36 months cumulative: **{metrics['recent_36_month_net_cumulative_10bps']:.6%}**",
        "",
        "A Phase0 PASS is post-publication Nikkei spot evidence only; true OSE confirmation remains mandatory."
    ])+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in out.items() if k not in {"monthly_records","daily_records"}},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
