from __future__ import annotations

import csv, hashlib, json, random, statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PREREG=ROOT/"config"/"jnu_intraday_momentum_reversion_true_jnu_g1_prereg.json"
PANEL=ROOT/"cloud_data"/"derived"/"jnu_momrev_mini_stage_a_g1.csv"
MANIFEST=ROOT/"cloud_data"/"manifests"/"jnu_momrev_mini_stage_a_g1_manifest.json"
RESULT=ROOT/"directional_results"/"jnu_momrev_true_ose_mini_stage_a_g1.json"
REPORT=ROOT/"directional_reports"/"jnu_momrev_true_ose_mini_stage_a_g1.md"

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for b in iter(lambda:fh.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def quantile_sorted(xs:list[float],q:float)->float:
    ys=sorted(xs)
    pos=(len(ys)-1)*q
    lo=int(pos); hi=min(lo+1,len(ys)-1); f=pos-lo
    return ys[lo]*(1-f)+ys[hi]*f

def bootstrap_mean(xs:list[float],samples:int,seed:int)->dict:
    rng=random.Random(seed)
    n=len(xs)
    means=[]
    for _ in range(samples):
        means.append(sum(xs[rng.randrange(n)] for _ in range(n))/n)
    prob=sum(m>0 for m in means)/samples
    return {
        "samples":samples,
        "seed":seed,
        "prob_mean_positive":prob,
        "one_sided_p":1.0-prob,
        "ci95":[quantile_sorted(means,0.025),quantile_sorted(means,0.975)]
    }

def holm(pvals:dict[str,float],alpha:float)->dict:
    ordered=sorted(pvals.items(),key=lambda x:x[1])
    checks=[]
    passed=True
    m=len(ordered)
    for i,(name,p) in enumerate(ordered):
        thr=alpha/(m-i)
        ok=p<=thr
        checks.append({"cell":name,"p":p,"threshold":thr,"pass":ok})
        if not ok:
            passed=False
            break
    return {"method":"Holm","alpha":alpha,"pass":passed,"checks":checks}

def main():
    prereg=json.loads(PREREG.read_text(encoding="utf-8"))
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("raw_data_cloud_uploaded") is not False:
        raise RuntimeError("fail closed: raw_data_cloud_uploaded must be false")
    if manifest.get("critical_data_quality_issues"):
        raise RuntimeError("fail closed: critical DQ issues remain")
    if manifest.get("derived_output_hash") != sha256_file(PANEL):
        raise RuntimeError("fail closed: panel hash mismatch")
    if manifest.get("stage")!="A_TRUE_OSE_MINI":
        raise RuntimeError("fail closed: wrong stage")
    if manifest.get("market_outcome_interpretation_performed") is not False:
        raise RuntimeError("fail closed: local builder interpreted outcome")

    rows=list(csv.DictReader(PANEL.open(encoding="utf-8")))
    min_days=1000
    bcfg=prereg["inference"]["bootstrap"]
    alpha=float(prereg["inference"]["family_correction"]["alpha"])

    cells={}
    for cid,prefix in [("H1_1M_MOMENTUM","h1"),("H2_10M_REVERSION","h2")]:
        dpay=[float(r[f"{prefix}_daily_mean_signal_payoff"]) for r in rows if r[f"{prefix}_daily_mean_signal_payoff"] not in ("",None)]
        correct=sum(int(r[f"{prefix}_correct"]) for r in rows)
        denom=sum(int(r[f"{prefix}_accuracy_denominator"]) for r in rows)
        acc=correct/denom if denom else None
        bs=bootstrap_mean(dpay,int(bcfg["resamples"]),int(bcfg["seed"]))
        mean_pay=statistics.fmean(dpay) if dpay else None
        passed=bool(
            len(dpay)>=min_days and
            mean_pay is not None and mean_pay>0 and
            acc is not None and acc>0.5 and
            bs["prob_mean_positive"]>=0.95
        )
        cells[cid]={
            "status":"CELL_PASS" if passed else "CELL_FAIL_TRUE_OSE_CURRENT_SPEC",
            "usable_days":len(dpay),
            "minimum_usable_days":min_days,
            "mean_daily_signal_payoff":mean_pay,
            "aggregate_directional_accuracy_nonzero_targets":acc,
            "correct_nonzero_targets":correct,
            "accuracy_denominator":denom,
            "bootstrap":bs
        }

    hc=holm({k:v["bootstrap"]["one_sided_p"] for k,v in cells.items()},alpha)
    all_cells=all(v["status"]=="CELL_PASS" for v in cells.values())
    passed=bool(all_cells and hc["pass"])
    status="TRUE_OSE_MINI_MOMREV_STAGE_A_PASS" if passed else "TRUE_OSE_MINI_MOMREV_STAGE_A_FAIL"

    result={
        "candidate_id":prereg["candidate_id"],
        "stage":"A_TRUE_OSE_MINI",
        "status":status,
        "stage_a_pass":passed,
        "role":"DIRECTIONAL_INFORMATION_GATE",
        "panel_days":len(rows),
        "cells":cells,
        "holm":hc,
        "derived_panel_sha256":sha256_file(PANEL),
        "manifest_sha256":sha256_file(MANIFEST),
        "next_rule":(
            "Proceed to exact JNU Micro Stage B with identical constructions and no retuning."
            if passed else
            "Close current family. Do not change horizons, use overlapping 10m windows, drop a failed cell, add filters, or let Micro rescue Stage A."
        ),
        "generated_at_utc":datetime.now(timezone.utc).isoformat()
    }
    RESULT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(
        "# True-OSE Mini momentum/reversion Stage A G1\n\n"
        f"- Status: **{status}**\n"
        f"- H1 1m momentum: {cells['H1_1M_MOMENTUM']['status']}; payoff={cells['H1_1M_MOMENTUM']['mean_daily_signal_payoff']}; accuracy={cells['H1_1M_MOMENTUM']['aggregate_directional_accuracy_nonzero_targets']}; Pboot={cells['H1_1M_MOMENTUM']['bootstrap']['prob_mean_positive']}\n"
        f"- H2 10m reversal: {cells['H2_10M_REVERSION']['status']}; payoff={cells['H2_10M_REVERSION']['mean_daily_signal_payoff']}; accuracy={cells['H2_10M_REVERSION']['aggregate_directional_accuracy_nonzero_targets']}; Pboot={cells['H2_10M_REVERSION']['bootstrap']['prob_mean_positive']}\n"
        f"- Holm family pass: {hc['pass']}\n\n"
        "Stage B is permitted only if Stage A passes both cells and the family correction.\n",
        encoding="utf-8"
    )
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
