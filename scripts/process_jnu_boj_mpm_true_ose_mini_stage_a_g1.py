from __future__ import annotations

import csv
import hashlib
import json
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PREREG=ROOT/"config"/"jnu_boj_mpm_true_ose_event_volatility_g1_prereg.json"
PANEL=ROOT/"cloud_data"/"derived"/"jnu_boj_mpm_mini_event_volatility_g1.csv"
MANIFEST=ROOT/"cloud_data"/"manifests"/"jnu_boj_mpm_mini_event_volatility_g1_manifest.json"
RESULT=ROOT/"event_volatility_results"/"jnu_boj_mpm_true_ose_mini_stage_a_g1.json"
REPORT=ROOT/"event_volatility_reports"/"jnu_boj_mpm_true_ose_mini_stage_a_g1.md"

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for b in iter(lambda:fh.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def quantile_sorted(xs:list[float],q:float)->float:
    if not xs:
        raise ValueError("empty")
    ys=sorted(xs)
    pos=(len(ys)-1)*q
    lo=int(pos); hi=min(lo+1,len(ys)-1); frac=pos-lo
    return ys[lo]*(1-frac)+ys[hi]*frac

def bootstrap_mean(xs:list[float],samples:int,seed:int)->dict:
    rng=random.Random(seed)
    n=len(xs)
    means=[]
    for _ in range(samples):
        means.append(sum(xs[rng.randrange(n)] for _ in range(n))/n)
    return {
        "samples":samples,
        "seed":seed,
        "prob_mean_positive":sum(m>0 for m in means)/samples,
        "ci95":[quantile_sorted(means,0.025),quantile_sorted(means,0.975)]
    }

def main()->None:
    prereg=json.loads(PREREG.read_text(encoding="utf-8"))
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("raw_data_cloud_uploaded") is not False:
        raise RuntimeError("fail closed: raw_data_cloud_uploaded must be false")
    if manifest.get("critical_data_quality_issues"):
        raise RuntimeError("fail closed: critical DQ issues remain")
    if manifest.get("derived_output_hash") != sha256_file(PANEL):
        raise RuntimeError("fail closed: aggregate panel hash mismatch")
    if manifest.get("stage")!="A_TRUE_OSE_MINI":
        raise RuntimeError("fail closed: wrong product stage")
    if manifest.get("market_outcome_interpretation_performed") is not False:
        raise RuntimeError("fail closed: local builder must not interpret outcome")

    rows=list(csv.DictReader(PANEL.open(encoding="utf-8")))
    effects=[float(r["log_event_to_baseline_rv_ratio"]) for r in rows]
    min_events=int(prereg["stage_a"]["minimum_usable_events"])
    if len(effects)<min_events:
        status="DATA_INCONCLUSIVE_TOO_FEW_USABLE_EVENTS"
        passed=False
        bs=None
        mean_effect=statistics.fmean(effects) if effects else None
        median_effect=statistics.median(effects) if effects else None
    else:
        mean_effect=statistics.fmean(effects)
        median_effect=statistics.median(effects)
        bcfg=prereg["stage_a"]["test"]["bootstrap"]
        bs=bootstrap_mean(effects,int(bcfg["resamples"]),int(bcfg["seed"]))
        threshold=float(bcfg["probability_mean_effect_positive_threshold"])
        passed=bool(mean_effect>0 and median_effect>0 and bs["prob_mean_positive"]>=threshold)
        status="TRUE_OSE_MINI_BOJ_EVENT_VOL_STAGE_A_PASS" if passed else "TRUE_OSE_MINI_BOJ_EVENT_VOL_STAGE_A_FAIL"

    result={
        "candidate_id":prereg["candidate_id"],
        "stage":"A_TRUE_OSE_MINI",
        "status":status,
        "stage_a_pass":passed,
        "role":"EVENT_RISK_STATE_ONLY_NOT_DIRECTIONAL_ALPHA",
        "usable_events":len(effects),
        "minimum_usable_events":min_events,
        "mean_log_event_to_baseline_rv_ratio":mean_effect,
        "median_log_event_to_baseline_rv_ratio":median_effect,
        "bootstrap":bs,
        "derived_panel_sha256":sha256_file(PANEL),
        "manifest_sha256":sha256_file(MANIFEST),
        "next_rule":(
            "Proceed to exact JNU Micro Stage B with identical transform/gate and no retuning."
            if passed else
            "Do not inspect/promote Micro Stage B statistics as a rescue. Close current family if this is a statistical FAIL."
        ),
        "generated_at_utc":datetime.now(timezone.utc).isoformat()
    }
    RESULT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(
        "# BOJ MPM true-OSE Mini event-volatility Stage A G1\n\n"
        f"- Status: **{status}**\n"
        f"- Usable events: {len(effects)}\n"
        f"- Mean log(EventRV/BaselineRV): {mean_effect}\n"
        f"- Median log(EventRV/BaselineRV): {median_effect}\n"
        f"- Bootstrap P(mean effect > 0): {None if bs is None else bs['prob_mean_positive']}\n"
        f"- Bootstrap 95% CI: {None if bs is None else bs['ci95']}\n\n"
        "This is an event/risk-state information test only. It is not directional alpha. "
        "Stage B is permitted only if Stage A passes the preregistered gate.\n",
        encoding="utf-8"
    )
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
