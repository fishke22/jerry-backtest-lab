from __future__ import annotations
import hashlib, io, json, math, random, statistics, zipfile
from pathlib import Path
import pandas as pd

ROOT=Path(r"D:\JERRY_BACKTEST_CLOUD_SYNC_20260831")
RAW=Path(r"D:\QROS\data\personal_licensed\225labo\mini\raw")
SIGNAL=Path(r"D:\QROS\data\derived\jnu_basis_change_g1\ose_mini_cash_basis_change_signal_panel_v1.json")
ALIGN=ROOT/"config"/"jnu_ose_mini_cash_basis_change_g1_subperiod_alignment.json"
PREREG=ROOT/"config"/"jnu_ose_mini_cash_basis_change_g1_prereg.json"
EXEC=ROOT/"config"/"jnu_ose_mini_cash_basis_change_g1_execution_cost_final.json"
OUT=Path(r"D:\Temp\jnu_ose_mini_cash_basis_change_phase1_result.json")
REPORT=Path(r"D:\Temp\jnu_ose_mini_cash_basis_change_phase1_report.md")

def sha_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def read_5m(zp:Path)->pd.DataFrame:
    with zipfile.ZipFile(zp) as z:
        names=z.namelist()
        if len(names)!=1: raise RuntimeError(f"{zp.name}: workbook count {len(names)}")
        raw=pd.read_excel(io.BytesIO(z.read(names[0])),sheet_name="5min",header=None)
    hidx=None
    for i in range(min(8,len(raw))):
        if "日付" in str(raw.iloc[i,0]) and "時間" in str(raw.iloc[i,1]):
            hidx=i; break
    if hidx is None: raise RuntimeError(f"{zp.name}: no 5min header")
    df=raw.iloc[hidx+1:,:7].copy()
    df.columns=["date","time","open","high","low","close","volume"]
    df["date"]=pd.to_datetime(df["date"],errors="coerce")
    df=df[df["date"].notna()].copy()
    def hhmm(v):
        s=str(v)
        if ":" in s:
            q=s.split(":")
            return f"{int(q[0]):02d}:{int(q[1]):02d}"
        return s[:5]
    df["hhmm"]=df["time"].map(hhmm)
    return df[["date","hhmm","open"]]

def cumulative(xs):
    z=1.0
    for x in xs: z*=1.0+x
    return z-1.0

def sharpe(xs):
    if len(xs)<2: return None
    sd=statistics.stdev(xs)
    if sd==0: return None
    return statistics.fmean(xs)/sd*math.sqrt(252.0)

def bootstrap(xs,block=20,samples=5000,seed=42):
    n=len(xs)
    if n<block: raise RuntimeError("sample shorter than bootstrap block")
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
        "block_trading_days":block,
        "seed":seed,
        "mean":statistics.fmean(xs),
        "prob_mean_positive":sum(x>0 for x in means)/samples,
        "ci95":[means[int(0.025*samples)],means[min(samples-1,int(0.975*samples))]],
        "lower_95":means[int(0.025*samples)]
    }

def main():
    sig=json.loads(SIGNAL.read_text(encoding="utf-8"))
    align=json.loads(ALIGN.read_text(encoding="utf-8"))
    pre=json.loads(PREREG.read_text(encoding="utf-8"))
    exe=json.loads(EXEC.read_text(encoding="utf-8"))
    if pre.get("directional_outcome_inspected") is not False: raise RuntimeError("prereg outcome guard failed")
    if sig.get("directional_outcome_inspected") is not False: raise RuntimeError("signal outcome guard failed")
    if align.get("directional_outcome_inspected") is not False: raise RuntimeError("alignment outcome guard failed")
    if sha_file(SIGNAL)!=align["signal_panel_sha256"]: raise RuntimeError("signal panel hash mismatch")
    if len(sig["records"])!=align["observations"]: raise RuntimeError("observation count mismatch")

    needed=set()
    for r in sig["records"]:
        needed.add((r["signal_date"],r["entry_time"]))
        needed.add((r["next_cash_date"],r["exit_time"]))

    bars={}
    for year in range(2012,2027):
        zp=RAW/f"N225minif_{year}.zip"
        df=read_5m(zp)
        for row in df.itertuples(index=False):
            d=row.date.date().isoformat()
            k=(d,row.hhmm)
            if k not in needed: continue
            try: op=float(row.open)
            except Exception: continue
            if k in bars and abs(bars[k]-op)>1e-12:
                raise RuntimeError(f"duplicate conflicting price {k}: {bars[k]} vs {op}")
            bars[k]=op
    missing=sorted(needed-set(bars))
    if missing: raise RuntimeError(f"missing entry/exit prices: {missing[:10]}")

    cuts=[]
    for i,sz in enumerate(align["subperiod_sizes"],1):
        cuts.extend([i]*sz)
    if len(cuts)!=len(sig["records"]): raise RuntimeError("subperiod sizes mismatch")

    rows=[]
    for r,subperiod in zip(sig["records"],cuts):
        entry=bars[(r["signal_date"],r["entry_time"])]
        exitp=bars[(r["next_cash_date"],r["exit_time"])]
        pos=int(r["signal_sign"])
        gross=pos*(exitp/entry-1.0)
        cost1=5.0/entry + 5.0/exitp
        cost2=10.0/entry + 10.0/exitp
        rows.append({
            "signal_date":r["signal_date"],
            "next_cash_date":r["next_cash_date"],
            "entry_time":r["entry_time"],
            "exit_time":r["exit_time"],
            "signal_sign":pos,
            "subperiod":subperiod,
            "entry_price":entry,
            "exit_price":exitp,
            "gross_return":gross,
            "primary_round_trip_cost_return":cost1,
            "stress_round_trip_cost_return":cost2,
            "net_return_1tick_each_side":gross-cost1,
            "net_return_2ticks_each_side":gross-cost2
        })

    primary=[r["net_return_1tick_each_side"] for r in rows]
    stress=[r["net_return_2ticks_each_side"] for r in rows]
    boot=bootstrap(primary)
    subs=[]
    for b in range(1,5):
        rr=[r for r in rows if r["subperiod"]==b]
        subs.append({
            "subperiod":b,
            "n":len(rr),
            "from":rr[0]["signal_date"],
            "to":rr[-1]["signal_date"],
            "net_cumulative_primary":cumulative([r["net_return_1tick_each_side"] for r in rr]),
            "net_cumulative_stress":cumulative([r["net_return_2ticks_each_side"] for r in rr]),
            "mean_daily_net_primary":statistics.fmean([r["net_return_1tick_each_side"] for r in rr])
        })
    pos_sub=sum(x["net_cumulative_primary"]>0 for x in subs)
    sh=sharpe(primary)
    metrics={
        "net_cumulative_primary":cumulative(primary),
        "net_cumulative_stress":cumulative(stress),
        "mean_daily_net_primary":statistics.fmean(primary),
        "annualized_active_day_sharpe_primary":sh,
        "bootstrap":boot,
        "positive_subperiods":pos_sub,
        "recent_504_net_cumulative_primary":cumulative(primary[-504:])
    }
    checks={
        "minimum_2500_complete_observations":len(rows)>=2500,
        "primary_net_cumulative_positive":metrics["net_cumulative_primary"]>0,
        "primary_annualized_sharpe_positive":(sh is not None and sh>0),
        "stress_net_cumulative_positive":metrics["net_cumulative_stress"]>0,
        "bootstrap_95_lower_mean_positive":boot["lower_95"]>0,
        "at_least_3_of_4_subperiods_positive":pos_sub>=3
    }
    passed=all(checks.values())
    status="TRUE_OSE_MINI_BASIS_CHANGE_STAGE_A_PASS_REQUIRES_EXACT_JNU_CONFIRMATION" if passed else "OSE_MINI_CASH_BASIS_CHANGE_STAGE_A_FAIL_TERMINAL_CURRENT_SPEC"
    out={
        "version":"1.0",
        "candidate_id":"OSE_MINI_CASH_BASIS_CHANGE_G1",
        "status":status,
        "stage_a_pass":passed,
        "validated_jnu_module":False,
        "validated_directional_edge":False,
        "signal_panel_sha256":sha_file(SIGNAL),
        "alignment_sha256":sha_file(ALIGN),
        "prereg_sha256":sha_file(PREREG),
        "execution_cost_sha256":sha_file(EXEC),
        "observations":len(rows),
        "positions":{
            "long":sum(r["signal_sign"]==1 for r in rows),
            "short":sum(r["signal_sign"]==-1 for r in rows),
            "flat":sum(r["signal_sign"]==0 for r in rows)
        },
        "metrics":metrics,
        "subperiods":subs,
        "checks":checks,
        "records":rows
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text("\n".join([
        "# OSE Mini Cash Basis Change G1 - Stage A","",
        f"- Status: **{status}**",
        f"- Observations: **{len(rows)}**",
        f"- Long / Short / Flat: **{out['positions']['long']} / {out['positions']['short']} / {out['positions']['flat']}**",
        f"- Primary cumulative (1 tick each side): **{metrics['net_cumulative_primary']:.6%}**",
        f"- Stress cumulative (2 ticks each side): **{metrics['net_cumulative_stress']:.6%}**",
        f"- Active-day annualized Sharpe: **{sh}**",
        f"- Bootstrap lower 95% mean: **{boot['lower_95']:.8f}**",
        f"- Positive subperiods: **{pos_sub}/4**",
        f"- Recent 504 cumulative: **{metrics['recent_504_net_cumulative_primary']:.6%}**",
        "",
        "Stage A PASS, if any, is true OSE Mini evidence but is not exact-JNU validation."
    ])+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in out.items() if k!="records"},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
