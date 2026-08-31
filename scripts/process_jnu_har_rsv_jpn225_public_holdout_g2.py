from __future__ import annotations

import hashlib
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "config" / "jnu_har_rsv_jpn225_public_holdout_g2_prereg.json"
RESULTS = ROOT / "volatility_results" / "jnu_har_rsv_jpn225_public_holdout_g2.json"
REPORTS = ROOT / "volatility_reports" / "jnu_har_rsv_jpn225_public_holdout_g2.md"
DERIVED = ROOT / "cloud_data" / "derived" / "jnu_har_rsv_jpn225_public_holdout_g2_daily_rv.csv.gz"
MANIFEST = ROOT / "cloud_data" / "manifests" / "jnu_har_rsv_jpn225_public_holdout_g2.json"
URL = "https://raw.githubusercontent.com/getdata-finance/jpn225-1m-ohlcv-index-historical-data/main/JPN225_1m.csv"


def fetch() -> bytes:
    req = urllib.request.Request(URL, headers={"User-Agent": "JerryBacktestLab-JPN225-G2/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def daily_panel(raw: bytes) -> pd.DataFrame:
    d = pd.read_csv(io.BytesIO(raw))
    d["datetime"] = pd.to_datetime(d["datetime"], utc=True, errors="coerce")
    for c in ["open", "high", "low", "close", "volume"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["datetime", "close"]).sort_values("datetime").set_index("datetime")
    d.index = d.index.tz_convert("Asia/Tokyo")
    mins = d.index.hour * 60 + d.index.minute
    am = (mins >= 9 * 60) & (mins < 11 * 60 + 30)
    pm = (mins >= 12 * 60 + 30) & (mins < 15 * 60)
    d = d.loc[am | pm, ["close"]].copy()
    mins = d.index.hour * 60 + d.index.minute
    d["part"] = np.where(mins < 12 * 60, "AM", "PM")
    d["trade_date"] = pd.Index(d.index.date)
    rows = []
    for (date, part), g in d.groupby(["trade_date", "part"], sort=True):
        s = g["close"].sort_index().resample("5min").last().dropna()
        r = np.log(s).diff().dropna()
        if len(r) < 5:
            continue
        rows.append({
            "trade_date": pd.Timestamp(date),
            "part": part,
            "rv": float(np.square(r).sum()),
            "rsv_pos": float(np.square(r[r > 0]).sum()),
            "rsv_neg": float(np.square(r[r < 0]).sum()),
            "n_5m_returns": int(len(r)),
        })
    p = pd.DataFrame(rows)
    if p.empty:
        raise RuntimeError("no session RV rows")
    out = p.groupby("trade_date").agg(rv=("rv", "sum"), rsv_pos=("rsv_pos", "sum"), rsv_neg=("rsv_neg", "sum"), n_5m_returns=("n_5m_returns", "sum"), session_parts=("part", "nunique"))
    out = out[(out.session_parts == 2) & (out.n_5m_returns >= 46)].copy()
    return out


def features(p: pd.DataFrame) -> pd.DataFrame:
    eps = 1e-12
    d = p.copy()
    d["log_rv"] = np.log(d.rv.clip(lower=eps))
    d["log_rsv_pos"] = np.log(d.rsv_pos.clip(lower=eps))
    d["log_rsv_neg"] = np.log(d.rsv_neg.clip(lower=eps))
    d["lag_d"] = d.log_rv.shift(1)
    d["lag_w"] = d.log_rv.shift(1).rolling(5).mean()
    d["lag_m"] = d.log_rv.shift(1).rolling(22).mean()
    d["lag_pos"] = d.log_rsv_pos.shift(1)
    d["lag_neg"] = d.log_rsv_neg.shift(1)
    return d


def expanding(d: pd.DataFrame, min_train: int = 60) -> pd.DataFrame:
    specs = {"HAR_RV": ["lag_d", "lag_w", "lag_m"], "HAR_RSV": ["lag_pos", "lag_neg", "lag_w", "lag_m"]}
    out = pd.DataFrame(index=d.index)
    out["actual"] = d.rv
    for name, cols in specs.items():
        pred = pd.Series(np.nan, index=d.index)
        for i in range(min_train, len(d)):
            train = d.iloc[:i][cols + ["log_rv"]].dropna()
            row = d.iloc[i][cols]
            if len(train) < min_train or row.isna().any():
                continue
            X = np.c_[np.ones(len(train)), train[cols].to_numpy(float)]
            y = train.log_rv.to_numpy(float)
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            pred.iloc[i] = max(float(np.exp(np.r_[1.0, row.to_numpy(float)] @ beta)), 1e-12)
        out[name] = pred
    return out.dropna()


def qlike(a: pd.Series, p: pd.Series) -> pd.Series:
    a = a.clip(lower=1e-12); p = p.clip(lower=1e-12)
    return a / p + np.log(p)


def bootstrap(x: pd.Series, block: int = 5, samples: int = 2000, seed: int = 42) -> dict:
    v = x.dropna().to_numpy(float); n = len(v)
    if n < 20:
        return {"n": n, "mean": float(v.mean()) if n else None, "prob_positive": None, "ci95": None}
    rng = np.random.default_rng(seed); starts = np.arange(n - block + 1); means = []
    for _ in range(samples):
        z = []
        while len(z) < n:
            s = int(rng.choice(starts)); z.extend(v[s:s + block])
        means.append(float(np.mean(z[:n])))
    lo, hi = np.quantile(means, [0.025, 0.975])
    return {"n": n, "mean": float(v.mean()), "prob_positive": float(np.mean(np.array(means) > 0)), "ci95": [float(lo), float(hi)]}


def main() -> None:
    prereg = json.loads(PREREG.read_text())
    raw = fetch(); source_sha = hashlib.sha256(raw).hexdigest()
    panel = daily_panel(raw); d = features(panel); fc = expanding(d, prereg["oos"]["minimum_training_days"])
    q0 = qlike(fc.actual, fc.HAR_RV); q1 = qlike(fc.actual, fc.HAR_RSV)
    m0 = (fc.actual - fc.HAR_RV) ** 2; m1 = (fc.actual - fc.HAR_RSV) ** 2
    qimp = q0 - q1; mimp = m0 - m1
    qb = bootstrap(qimp); mb = bootstrap(mimp)
    beats_both = float(qimp.mean()) > 0 and float(mimp.mean()) > 0
    p_gate = max(qb.get("prob_positive") or 0.0, mb.get("prob_positive") or 0.0) >= 0.95
    status = "CURRENT_SAMPLE_PROXY_CONSISTENT" if beats_both and p_gate else "CURRENT_SAMPLE_PROXY_NOT_CONFIRMED"
    result = {
        "candidate_id": prereg["candidate_id"], "status": status, "formal_true_jnu_status": "STILL_PENDING_TRUE_OSE",
        "promotion_power": "NONE_TO_TRUE_JNU", "source_url": URL, "source_sha256": source_sha,
        "panel_days": int(len(panel)), "oos_days": int(len(fc)), "oos_from": str(fc.index.min().date()) if len(fc) else None, "oos_to": str(fc.index.max().date()) if len(fc) else None,
        "losses": {"HAR_RV": {"qlike": float(q0.mean()), "mse": float(m0.mean())}, "HAR_RSV": {"qlike": float(q1.mean()), "mse": float(m1.mean())}},
        "improvement": {"qlike": float(qimp.mean()), "mse": float(mimp.mean()), "qlike_bootstrap": qb, "mse_bootstrap": mb},
        "guardrail": "Proxy consistency is not true-JNU PASS and has no directional-alpha role.", "generated_at_utc": datetime.now(timezone.utc).isoformat()
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True); REPORTS.parent.mkdir(parents=True, exist_ok=True); DERIVED.parent.mkdir(parents=True, exist_ok=True); MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(DERIVED, compression="gzip")
    manifest = {"candidate_id": prereg["candidate_id"], "source_url": URL, "source_sha256": source_sha, "raw_persisted_in_repo": False, "derived_path": str(DERIVED.relative_to(ROOT)), "derived_sha256": hashlib.sha256(DERIVED.read_bytes()).hexdigest(), "license_note": prereg["source"]["license"]}
    RESULTS.write_text(json.dumps(result, indent=2) + "\n")
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    REPORTS.write_text(f"# JNU HAR-RSV public JPN225 holdout G2\n\n- Status: **{status}**\n- Panel days: {len(panel)}\n- OOS days: {len(fc)}\n- QLIKE improvement: {qimp.mean():.12g}\n- MSE improvement: {mimp.mean():.12g}\n- P(QLIKE improvement > 0): {qb.get('prob_positive')}\n- P(MSE improvement > 0): {mb.get('prob_positive')}\n\nThis is a public Japan 225 proxy holdout only. It cannot promote HAR-RSV to validated JNU; true-OSE mini Stage A and JNU micro Stage B remain mandatory.\n")

if __name__ == "__main__":
    main()
