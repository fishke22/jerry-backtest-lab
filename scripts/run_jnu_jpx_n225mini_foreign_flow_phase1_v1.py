from __future__ import annotations
import csv, hashlib, json, math, random, statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ALIGN=ROOT/"flow_results"/"jnu_jpx_n225mini_foreign_flow_alignment_v1.json"
PREREG=ROOT/"config"/"jnu_jpx_n225mini_foreign_flow_sign_g1_prereg_min.json"
RETWIN=ROOT/"config"/"jnu_jpx_n225mini_foreign_flow_return_window_v1.json"
FRED=Path(r"D:\Temp\nikkei225_2016_20260902.csv")
OUT=Path(r"D:\Temp\jnu_jpx_foreign_flow_phase1_result.json")
REPORT=Path(r"D:\Temp\jnu_jpx_foreign_flow_phase1_report.md")

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def load_prices()->dict[str,float]:
    out={}
    with FRED.open(encoding="utf-8",newline="") as f:
        rd=csv.DictReader(f)
        for r in rd:
            v=(r.get("NIKKEI225") or "").strip()
            if v in {"",".","NA","NaN"}: continue
            out[r["observation_date"]]=float(v)
    return out

def cumulative(xs:list[float])->float:
    v=1.0
    for x in xs:
        v*=1.0+x
    return v-1.0

def sharpe(xs:list[float])->float|None:
    if len(xs)<2: return None
    sd=statistics.stdev(xs)
    if sd==0: return None
    return statistics.fmean(xs)/sd*math.sqrt(52.0)

def moving_block_bootstrap(xs:list[float],block:int,samples:int,seed:int)->dict:
    n=len(xs)
    if n<block: raise RuntimeError("bootstrap sample shorter than block")
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
    lo=means[int(0.025*samples)]
    hi=means[min(samples-1,int(0.975*samples))]
    return {
        "samples":samples,
        "block_weeks":block,
        "seed":seed,
        "mean":statistics.fmean(xs),
        "prob_mean_positive":sum(1 for x in means if x>0)/samples,
        "ci95":[lo,hi],
        "lower_95":lo,
    }

def main():
    prereg=json.loads(PREREG.read_text(encoding="utf-8"))
    align=json.loads(ALIGN.read_text(encoding="utf-8"))
    retwin=json.loads(RETWIN.read_text(encoding="utf-8"))
    if prereg.get("directional_outcome_inspected") is not False:
        raise RuntimeError("prereg outcome guard failed")
    if align.get("status")!="ALIGNMENT_FROZEN_BEFORE_PRICE_VALUE_READ":
        raise RuntimeError("alignment not frozen")
    if align.get("price_values_parsed") is not False:
        raise RuntimeError("alignment already parsed price values")

    px=load_prices()
    rows=[]
    prev=0
    for a in align["records"]:
        entry=a["entry_date"]; exitd=a["exit_date"]
        if entry not in px or exitd not in px:
            raise RuntimeError(f"aligned price missing {entry}->{exitd}")
        gross=px[exitd]/px[entry]-1.0
        pos=int(a["foreign_flow_sign"])
        turnover=abs(pos-prev)
        strat=pos*gross
        net10=strat-turnover*(10/10000)
        net20=strat-turnover*(20/10000)
        rows.append({
            **a,
            "entry_close":px[entry],
            "exit_close":px[exitd],
            "underlying_return":gross,
            "position":pos,
            "turnover":turnover,
            "strategy_gross_return":strat,
            "net_return_10bps":net10,
            "net_return_20bps":net20,
        })
        prev=pos

    n=len(rows)
    if n!=align["eligible_complete_observations"]:
        raise RuntimeError("record count changed")
    net10=[r["net_return_10bps"] for r in rows]
    net20=[r["net_return_20bps"] for r in rows]
    boot=moving_block_bootstrap(net10,5,5000,42)

    subs=[]
    for b in range(1,5):
        rr=[r for r in rows if r["subperiod"]==b]
        subs.append({
            "subperiod":b,
            "n":len(rr),
            "from":rr[0]["publication_date"],
            "to":rr[-1]["publication_date"],
            "net_cumulative_10bps":cumulative([r["net_return_10bps"] for r in rr]),
            "net_cumulative_20bps":cumulative([r["net_return_20bps"] for r in rr]),
            "mean_weekly_net_10bps":statistics.fmean([r["net_return_10bps"] for r in rr]),
        })
    pos_sub=sum(1 for x in subs if x["net_cumulative_10bps"]>0)
    recent=rows[-104:]
    recent_cum=cumulative([r["net_return_10bps"] for r in recent])

    primary_cum=cumulative(net10)
    stress_cum=cumulative(net20)
    shp=sharpe(net10)
    checks={
        "minimum_300_weeks":n>=300,
        "net_cumulative_10bps_positive":primary_cum>0,
        "annualized_sharpe_positive":(shp is not None and shp>0),
        "stress_20bps_cumulative_positive":stress_cum>0,
        "bootstrap_95_lower_mean_positive":boot["lower_95"]>0,
        "at_least_3_of_4_subperiods_positive":pos_sub>=3,
    }
    passed=all(checks.values())
    status="HISTORICAL_OOS_PASS_PROXY_REQUIRES_TRUE_JNU_CONFIRMATION" if passed else "JPX_FOREIGN_FLOW_DIRECTIONAL_PHASE1_FAIL_TERMINAL_CURRENT_SPEC"
    result={
        "version":"1.0",
        "candidate_id":"JPX_N225MINI_FOREIGN_FLOW_SIGN_G1",
        "status":status,
        "phase1_pass":passed,
        "validated_jnu_module":False,
        "validated_directional_edge":False,
        "alignment_sha256":sha(ALIGN),
        "prereg_sha256":sha(PREREG),
        "return_window_sha256":sha(RETWIN),
        "fred_csv_sha256":sha(FRED),
        "observations":n,
        "positions":{
            "long":sum(1 for r in rows if r["position"]==1),
            "short":sum(1 for r in rows if r["position"]==-1),
            "flat":sum(1 for r in rows if r["position"]==0),
        },
        "metrics":{
            "net_cumulative_10bps":primary_cum,
            "net_cumulative_20bps":stress_cum,
            "mean_weekly_net_10bps":statistics.fmean(net10),
            "annualized_sharpe_10bps":shp,
            "bootstrap":boot,
            "positive_subperiods":pos_sub,
            "recent_104_net_cumulative_10bps":recent_cum,
        },
        "subperiods":subs,
        "checks":checks,
        "records":rows,
    }
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    lines=[
        "# JPX Nikkei 225 mini Foreign Flow Sign G1 - Phase 1",
        "",
        f"- Status: **{status}**",
        f"- Observations: **{n}**",
        f"- Long / Short / Flat: **{result['positions']['long']} / {result['positions']['short']} / {result['positions']['flat']}**",
        f"- Net cumulative 10bps: **{primary_cum:.6%}**",
        f"- Net cumulative 20bps: **{stress_cum:.6%}**",
        f"- Annualized Sharpe: **{shp}**",
        f"- Bootstrap lower 95% mean weekly net: **{boot['lower_95']:.8f}**",
        f"- Positive subperiods: **{pos_sub}/4**",
        f"- Recent 104 cumulative: **{recent_cum:.6%}**",
        "",
        "Phase 1 is a public Nikkei proxy/post-publication historical test. A PASS is not exact-JNU validation.",
    ]
    REPORT.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="records"},indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
