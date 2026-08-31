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
STAGE_A=ROOT/"event_volatility_results"/"jnu_boj_mpm_true_ose_mini_stage_a_g1.json"
PANEL=ROOT/"cloud_data"/"derived"/"jnu_boj_mpm_micro_event_volatility_g1.csv"
MANIFEST=ROOT/"cloud_data"/"manifests"/"jnu_boj_mpm_micro_event_volatility_g1_manifest.json"
RESULT=ROOT/"event_volatility_results"/"jnu_boj_mpm_exact_jnu_micro_stage_b_g1.json"
REPORT=ROOT/"event_volatility_reports"/"jnu_boj_mpm_exact_jnu_micro_stage_b_g1.md"

def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for b in iter(lambda:fh.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def quantile_sorted(xs:list[float],q:float)->float:
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
    stage_a=json.loads(STAGE_A.read_text(encoding="utf-8"))
    if stage_a.get("status")!="TRUE_OSE_MINI_BOJ_EVENT_VOL_STAGE_A_PASS" or stage_a.get("stage_a_pass") is not True:
        raise RuntimeError("fail closed: Stage A PASS prerequisite not satisfied")

    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("raw_data_cloud_uploaded") is not False:
        raise RuntimeError("fail closed: raw_data_cloud_uploaded must be false")
    if manifest.get("critical_data_quality_issues"):
        raise RuntimeError("fail closed: critical DQ issues remain")
    if manifest.get("derived_output_hash") != sha256_file(PANEL):
        raise RuntimeError("fail closed: Micro aggregate panel hash mismatch")
    if manifest.get("stage")!="B_EXACT_JNU_MICRO":
        raise RuntimeError("fail closed: wrong product stage")
    if manifest.get("market_outcome_interpretation_performed") is not False:
        raise RuntimeError("fail closed: local builder must not interpret outcome")

    rows=list(csv.DictReader(PANEL.open(encoding="utf-8")))
    effects=[float(r["log_event_to_baseline_rv_ratio"]) for r in rows]
    min_events=int(prereg["stage_b"]["minimum_usable_events"])
    if len(effects)<min_events:
        status="DATA_INCONCLUSIVE_TOO_FEW_USABLE_EVENTS"
        passed=False
        mean_effect=statistics.fmean(effects) if effects else None
        median_effect=statistics.median(effects) if effects else None
        bs=None
    else:
        mean_effect=statistics.fmean(effects)
        median_effect=statistics.median(effects)
        # Stage B is frozen to the same bootstrap configuration as Stage A.
        bcfg=prereg["stage_a"]["test"]["bootstrap"]
        bs=bootstrap_mean(effects,int(bcfg["resamples"]),int(bcfg["seed"]))
        threshold=float(bcfg["probability_mean_effect_positive_threshold"])
        passed=bool(mean_effect>0 and median_effect>0 and bs["prob_mean_positive"]>=threshold)
        status="TRUE_JNU_MICRO_BOJ_EVENT_VOL_STAGE_B_PASS" if passed else "TRUE_JNU_MICRO_BOJ_EVENT_VOL_STAGE_B_FAIL"

    result={
        "candidate_id":prereg["candidate_id"],
        "stage":"B_EXACT_JNU_MICRO",
        "status":status,
        "stage_b_pass":passed,
        "stage_a_prerequisite":"TRUE_OSE_MINI_BOJ_EVENT_VOL_STAGE_A_PASS",
        "role":"EVENT_RISK_STATE_ONLY_NOT_DIRECTIONAL_ALPHA",
        "usable_events":len(effects),
        "minimum_usable_events":min_events,
        "mean_log_event_to_baseline_rv_ratio":mean_effect,
        "median_log_event_to_baseline_rv_ratio":median_effect,
        "bootstrap":bs,
        "derived_panel_sha256":sha256_file(PANEL),
        "manifest_sha256":sha256_file(MANIFEST),
        "promotion_pipeline_stage":3 if passed else None,
        "promotion_state_if_pass":"EVENT_RISK_INFORMATION_STATE_CANDIDATE",
        "next_rule":(
            "Stage 3 true-target event/risk confirmation passes. Any entry blackout, size reduction, stop widening, or confidence rule must be separately preregistered and validated downstream."
            if passed else
            "Close current family. Do not rescue by changing windows, event classifications, or policy-direction splits."
        ),
        "generated_at_utc":datetime.now(timezone.utc).isoformat()
    }
    RESULT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(
        "# BOJ MPM exact-JNU Micro event-volatility Stage B G1\n\n"
        f"- Status: **{status}**\n"
        f"- Usable events: {len(effects)}\n"
        f"- Mean log(EventRV/BaselineRV): {mean_effect}\n"
        f"- Median log(EventRV/BaselineRV): {median_effect}\n"
        f"- Bootstrap P(mean effect > 0): {None if bs is None else bs['prob_mean_positive']}\n"
        f"- Bootstrap 95% CI: {None if bs is None else bs['ci95']}\n\n"
        "This is exact-product JNU event/risk-state evidence only. A PASS does not create directional alpha or a validated live risk rule.\n",
        encoding="utf-8"
    )
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
