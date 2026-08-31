from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "config" / "jnu_har_rsv_true_ose_mini_stage_a_g1_prereg.json"
PANEL = ROOT / "cloud_data" / "derived" / "jnu_225labo_mini_daily_rvrsv_v1.csv"
MANIFEST = ROOT / "cloud_data" / "manifests" / "jnu_225labo_mini_daily_rvrsv_v1_manifest.json"
RESULT = ROOT / "volatility_results" / "jnu_har_rsv_true_ose_mini_stage_a_g1.json"
REPORT = ROOT / "volatility_reports" / "jnu_har_rsv_true_ose_mini_stage_a_g1.md"


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


def load_and_gate() -> tuple[pd.DataFrame, dict, dict]:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
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
    d = d[d["n_5m_returns"] >= int(prereg["data_integrity"]["minimum_5m_returns_per_day"])].copy()
    if len(d) < int(prereg["oos"]["minimum_training_days"]) + 30:
        raise RuntimeError(f"insufficient gated days: {len(d)}")
    return d, manifest, prereg


def features(panel: pd.DataFrame) -> pd.DataFrame:
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


def expanding(d: pd.DataFrame, min_train: int) -> pd.DataFrame:
    specs = {
        "HAR_RV": ["lag_d", "lag_w", "lag_m"],
        "HAR_RSV": ["lag_pos", "lag_neg", "lag_w", "lag_m"],
    }
    out = pd.DataFrame(index=d.index)
    out["actual"] = d["rv_5m"]
    for name, cols in specs.items():
        pred = pd.Series(np.nan, index=d.index, dtype=float)
        for i in range(min_train, len(d)):
            train = d.iloc[:i][cols + ["log_rv"]].dropna()
            row = d.iloc[i][cols]
            if len(train) < min_train or row.isna().any():
                continue
            X = np.c_[np.ones(len(train)), train[cols].to_numpy(float)]
            y = train["log_rv"].to_numpy(float)
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            pred.iloc[i] = max(float(np.exp(np.r_[1.0, row.to_numpy(float)] @ beta)), 1e-12)
        out[name] = pred
    return out.dropna()


def main() -> None:
    panel, manifest, prereg = load_and_gate()
    d = features(panel)
    fc = expanding(d, int(prereg["oos"]["minimum_training_days"]))

    q0 = qlike(fc["actual"], fc["HAR_RV"])
    q1 = qlike(fc["actual"], fc["HAR_RSV"])
    m0 = (fc["actual"] - fc["HAR_RV"]) ** 2
    m1 = (fc["actual"] - fc["HAR_RSV"]) ** 2
    qimp = q0 - q1
    mimp = m0 - m1

    bcfg = prereg["oos"]["bootstrap"]
    qb = block_bootstrap(qimp, int(bcfg["block_days"]), int(bcfg["samples"]), int(bcfg["seed"]))
    mb = block_bootstrap(mimp, int(bcfg["block_days"]), int(bcfg["samples"]), int(bcfg["seed"]))

    recent_from = pd.Timestamp(prereg["stability_gate"]["recent_period_from"])
    recent_mask = fc.index >= recent_from
    recent_q = float(qimp.loc[recent_mask].mean()) if recent_mask.any() else None
    recent_m = float(mimp.loc[recent_mask].mean()) if recent_mask.any() else None

    beats_both = float(qimp.mean()) > 0 and float(mimp.mean()) > 0
    recent_ok = recent_q is not None and recent_m is not None and recent_q >= 0 and recent_m >= 0
    bootstrap_ok = max(qb.get("prob_positive") or 0.0, mb.get("prob_positive") or 0.0) >= 0.95
    stage_a_pass = bool(beats_both and recent_ok and bootstrap_ok)

    status = "TRUE_OSE_MINI_STAGE_A_PASS" if stage_a_pass else "TRUE_OSE_MINI_STAGE_A_FAIL"
    result = {
        "candidate_id": prereg["candidate_id"],
        "status": status,
        "stage_a_pass": stage_a_pass,
        "role": "VOLATILITY_RISK_STATE_ONLY_NOT_DIRECTIONAL_ALPHA",
        "source": "true OSE Nikkei 225 Mini daily RV/RSV derived locally from 225Labo 5-minute data",
        "raw_data_cloud_uploaded": False,
        "derived_panel_sha256": sha256_file(PANEL),
        "manifest_sha256": sha256_file(MANIFEST),
        "panel_days_before_min_returns_gate": int(len(pd.read_csv(PANEL))),
        "panel_days_after_gate": int(len(panel)),
        "oos_days": int(len(fc)),
        "oos_from": str(fc.index.min().date()),
        "oos_to": str(fc.index.max().date()),
        "losses": {
            "HAR_RV": {"qlike": float(q0.mean()), "mse": float(m0.mean())},
            "HAR_RSV": {"qlike": float(q1.mean()), "mse": float(m1.mean())},
        },
        "improvement": {
            "qlike": float(qimp.mean()),
            "mse": float(mimp.mean()),
            "qlike_bootstrap": qb,
            "mse_bootstrap": mb,
            "recent_period_from": str(recent_from.date()),
            "recent_qlike_improvement": recent_q,
            "recent_mse_improvement": recent_m,
        },
        "next_rule": (
            "Proceed to frozen JNU Micro Stage B without retuning."
            if stage_a_pass
            else "Do not use a short Micro sample to rescue Stage A; family fails true-OSE long-history confirmation."
        ),
        "measurement_qa_1m_deferred": bool(manifest.get("measurement_qa_1m_deferred")),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    RESULT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# JNU HAR-RSV True-OSE Mini Stage A G1\n\n"
        f"- Status: **{status}**\n"
        f"- Gated panel days: {len(panel)}\n"
        f"- OOS days: {len(fc)} ({result['oos_from']} → {result['oos_to']})\n"
        f"- QLIKE improvement HAR_RV→HAR_RSV: {qimp.mean():.12g}\n"
        f"- MSE improvement HAR_RV→HAR_RSV: {mimp.mean():.12g}\n"
        f"- Pboot(QLIKE improvement>0): {qb.get('prob_positive')}\n"
        f"- Pboot(MSE improvement>0): {mb.get('prob_positive')}\n"
        f"- Recent QLIKE improvement ({recent_from.date()}+): {recent_q}\n"
        f"- Recent MSE improvement ({recent_from.date()}+): {recent_m}\n\n"
        "This is the preregistered true-OSE Mini long-history Stage A for the HAR-RSV risk-state family. "
        "It is not directional alpha. Stage A PASS still requires exact-product JNU Micro Stage B before admission.\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
