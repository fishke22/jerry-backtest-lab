from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "config" / "jnu_har_rsv_jnu_micro_stage8_forward_g1_prereg.json"
STAGE_A = ROOT / "volatility_results" / "jnu_har_rsv_true_ose_mini_stage_a_g1.json"
STAGE_B = ROOT / "volatility_results" / "jnu_har_rsv_jnu_micro_stage_b_g1.json"
PANEL = ROOT / "cloud_data" / "derived" / "jnu_225labo_micro_daily_rvrsv_v1.csv"
MANIFEST = ROOT / "cloud_data" / "manifests" / "jnu_225labo_micro_daily_rvrsv_v1_manifest.json"
RESULT = ROOT / "volatility_results" / "jnu_har_rsv_jnu_micro_stage8_forward_g1.json"
REPORT = ROOT / "volatility_reports" / "jnu_har_rsv_jnu_micro_stage8_forward_g1.md"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def qlike(actual: pd.Series, pred: pd.Series) -> pd.Series:
    a = actual.clip(lower=1e-12)
    p = pred.clip(lower=1e-12)
    return a / p + np.log(p)


def block_bootstrap(values: pd.Series, block: int, samples: int, seed: int) -> dict:
    x = values.dropna().to_numpy(float)
    n = len(x)
    if n < 30:
        return {"n": n, "mean": float(np.mean(x)) if n else None, "prob_positive": None, "ci95": None}
    block = max(1, min(block, n))
    rng = np.random.default_rng(seed)
    starts = np.arange(0, n - block + 1)
    means = np.empty(samples, dtype=float)
    for i in range(samples):
        acc: list[float] = []
        while len(acc) < n:
            start = int(rng.choice(starts))
            acc.extend(x[start:start + block])
        means[i] = float(np.mean(acc[:n]))
    lo, hi = np.quantile(means, [0.025, 0.975])
    return {
        "n": n,
        "mean": float(np.mean(x)),
        "prob_positive": float(np.mean(means > 0)),
        "ci95": [float(lo), float(hi)],
    }


def load_inputs() -> tuple[pd.DataFrame, dict, dict]:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    stage_a = json.loads(STAGE_A.read_text(encoding="utf-8"))
    stage_b = json.loads(STAGE_B.read_text(encoding="utf-8"))
    if stage_a.get("status") != "TRUE_OSE_MINI_STAGE_A_PASS":
        raise RuntimeError("fail closed: Stage A PASS prerequisite not satisfied")
    if stage_b.get("status") != "TRUE_JNU_MICRO_STAGE_B_PASS":
        raise RuntimeError("fail closed: Stage B PASS prerequisite not satisfied")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("raw_data_cloud_uploaded") is not False:
        raise RuntimeError("fail closed: raw_data_cloud_uploaded must be false")
    critical = manifest.get("critical_data_quality_issues")
    if not isinstance(critical, list) or critical:
        raise RuntimeError(f"fail closed: unresolved critical DQ issues: {critical}")
    if manifest.get("derived_output_hash") != sha256_file(PANEL):
        raise RuntimeError("fail closed: derived panel hash does not match manifest")

    d = pd.read_csv(PANEL)
    required = {
        "trading_date", "rv_5m", "rsv_pos_5m", "rsv_neg_5m",
        "n_5m_returns", "session_coverage_ratio",
    }
    missing = sorted(required - set(d.columns))
    if missing:
        raise RuntimeError(f"missing derived columns: {missing}")
    d["trading_date"] = pd.to_datetime(d["trading_date"], errors="coerce")
    for c in ["rv_5m", "rsv_pos_5m", "rsv_neg_5m", "n_5m_returns", "session_coverage_ratio"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["trading_date", "rv_5m", "rsv_pos_5m", "rsv_neg_5m", "n_5m_returns"])
    d = d.sort_values("trading_date").drop_duplicates("trading_date", keep="last").set_index("trading_date")
    d = d[d["n_5m_returns"] >= int(prereg["frozen_models"]["min_5m_returns_per_day"])].copy()
    return d, manifest, prereg


def feature_frame(panel: pd.DataFrame) -> pd.DataFrame:
    eps = 1e-12
    d = panel.copy()
    d["log_rv"] = np.log(d["rv_5m"].clip(lower=eps))
    d["log_rsv_pos"] = np.log(d["rsv_pos_5m"].clip(lower=eps))
    d["log_rsv_neg"] = np.log(d["rsv_neg_5m"].clip(lower=eps))
    d["lag_d"] = d["log_rv"].shift(1)
    d["lag_w"] = d["log_rv"].shift(1).rolling(5).mean()
    d["lag_m"] = d["log_rv"].shift(1).rolling(22).mean()
    d["lag_pos"] = d["log_rsv_pos"].shift(1)
    d["lag_neg"] = d["log_rsv_neg"].shift(1)
    return d


def fit_beta(train: pd.DataFrame, cols: list[str]) -> np.ndarray:
    t = train[cols + ["log_rv"]].dropna()
    if len(t) < 504:
        raise RuntimeError(f"fail closed: insufficient pre-holdout training rows: {len(t)}")
    X = np.c_[np.ones(len(t)), t[cols].to_numpy(float)]
    y = t["log_rv"].to_numpy(float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta


def fixed_predict(d: pd.DataFrame, beta: np.ndarray, cols: list[str], index: pd.DatetimeIndex) -> pd.Series:
    out = pd.Series(np.nan, index=index, dtype=float)
    for ts in index:
        row = d.loc[ts, cols]
        if row.isna().any():
            continue
        out.loc[ts] = max(float(np.exp(np.r_[1.0, row.to_numpy(float)] @ beta)), 1e-12)
    return out


def write_result(result: dict) -> None:
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if result["status"] == "STAGE8_FORWARD_HOLDOUT_PENDING_INSUFFICIENT_NEW_DATA":
        text = (
            "# JNU HAR-RSV Stage8 Forward Holdout G1\n\n"
            f"- Status: **{result['status']}**\n"
            f"- New eligible days available: **{result['available_new_days']} / {result['required_new_days']}**\n"
            f"- Remaining days: **{result['remaining_new_days']}**\n"
            "- Partial holdout performance: **PROHIBITED / NOT COMPUTED**\n"
        )
    else:
        m = result["holdout_metrics"]
        text = (
            "# JNU HAR-RSV Stage8 Forward Holdout G1\n\n"
            f"- Status: **{result['status']}**\n"
            f"- Holdout days: **{result['holdout_days']}**\n"
            f"- QLIKE improvement: **{m['qlike_improvement']:.12g}**\n"
            f"- MSE improvement: **{m['mse_improvement']:.12g}**\n"
            f"- Pboot QLIKE+: **{m['qlike_bootstrap']['prob_positive']}**\n"
            f"- Pboot MSE+: **{m['mse_bootstrap']['prob_positive']}**\n"
            "- Role remains volatility/risk-state only; no directional-alpha interpretation.\n"
        )
    REPORT.write_text(text, encoding="utf-8")


def main() -> None:
    panel, manifest, prereg = load_inputs()
    cutoff = pd.Timestamp(prereg["source"]["pre_holdout_cutoff"])
    required_days = int(prereg["holdout"]["length_trading_days"])
    pre = panel.loc[panel.index <= cutoff].copy()
    post = panel.loc[panel.index > cutoff].copy()

    base = {
        "candidate_id": prereg["candidate_id"],
        "prereg_sha256": sha256_file(PREREG),
        "derived_panel_sha256": sha256_file(PANEL),
        "manifest_sha256": sha256_file(MANIFEST),
        "pre_holdout_cutoff": cutoff.date().isoformat(),
        "pre_holdout_days": int(len(pre)),
        "available_new_days": int(len(post)),
        "required_new_days": required_days,
        "raw_data_cloud_uploaded": False,
        "role": "VOLATILITY_RISK_STATE_ONLY_NOT_DIRECTIONAL_ALPHA",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    if len(post) < required_days:
        result = {
            **base,
            "status": "STAGE8_FORWARD_HOLDOUT_PENDING_INSUFFICIENT_NEW_DATA",
            "remaining_new_days": required_days - int(len(post)),
            "partial_holdout_performance_computed": False,
            "holdout_metrics_revealed": False,
        }
        write_result(result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    holdout_idx = post.index[:required_days]
    d = feature_frame(pd.concat([pre, post.loc[:holdout_idx[-1]]]))
    beta_rv = fit_beta(d.loc[d.index <= cutoff], ["lag_d", "lag_w", "lag_m"])
    beta_rsv = fit_beta(d.loc[d.index <= cutoff], ["lag_pos", "lag_neg", "lag_w", "lag_m"])
    p0 = fixed_predict(d, beta_rv, ["lag_d", "lag_w", "lag_m"], holdout_idx)
    p1 = fixed_predict(d, beta_rsv, ["lag_pos", "lag_neg", "lag_w", "lag_m"], holdout_idx)
    actual = d.loc[holdout_idx, "rv_5m"]
    fc = pd.DataFrame({"actual": actual, "HAR_RV": p0, "HAR_RSV": p1}).dropna()
    if len(fc) != required_days:
        raise RuntimeError(f"fail closed: expected {required_days} scored holdout days, got {len(fc)}")

    qimp = qlike(fc["actual"], fc["HAR_RV"]) - qlike(fc["actual"], fc["HAR_RSV"])
    mimp = (fc["actual"] - fc["HAR_RV"]) ** 2 - (fc["actual"] - fc["HAR_RSV"]) ** 2
    bcfg = prereg["evaluation"]["bootstrap"]
    qb = block_bootstrap(qimp, int(bcfg["block_days"]), int(bcfg["samples"]), int(bcfg["seed"]))
    mb = block_bootstrap(mimp, int(bcfg["block_days"]), int(bcfg["samples"]), int(bcfg["seed"]))
    checks = {
        "qlike_improvement_positive": float(qimp.mean()) > 0,
        "mse_improvement_positive": float(mimp.mean()) > 0,
        "bootstrap_one_metric_ge_0_95": max(qb["prob_positive"] or 0.0, mb["prob_positive"] or 0.0) >= 0.95,
        "exactly_126_days": len(fc) == required_days,
        "zero_critical_dq": True,
    }
    passed = all(checks.values())
    status = "STAGE8_FORWARD_HOLDOUT_PASS" if passed else "STAGE8_FORWARD_HOLDOUT_FAIL_CURRENT_SPEC"
    result = {
        **base,
        "status": status,
        "holdout_days": int(len(fc)),
        "holdout_from": fc.index.min().date().isoformat(),
        "holdout_to": fc.index.max().date().isoformat(),
        "partial_holdout_performance_computed": False,
        "holdout_metrics_revealed": True,
        "checks": checks,
        "holdout_metrics": {
            "qlike_improvement": float(qimp.mean()),
            "mse_improvement": float(mimp.mean()),
            "qlike_bootstrap": qb,
            "mse_bootstrap": mb,
        },
        "next_rule": (
            "Proceed to Stage9 role-consistent validation review only; no directional promotion."
            if passed
            else "Terminal fail current Stage8 spec; no holdout rescue or retuning."
        ),
    }
    write_result(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
