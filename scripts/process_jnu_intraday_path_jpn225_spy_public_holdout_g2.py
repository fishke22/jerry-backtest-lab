from __future__ import annotations

import hashlib
import io
import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "config" / "jnu_intraday_path_jpn225_spy_public_holdout_g2_prereg.json"
RESULT = ROOT / "intraday_path_results" / "jnu_intraday_path_jpn225_spy_public_holdout_g2.json"
REPORT = ROOT / "intraday_path_reports" / "jnu_intraday_path_jpn225_spy_public_holdout_g2.md"
DERIVED = ROOT / "cloud_data" / "derived" / "jnu_intraday_path_jpn225_spy_public_holdout_g2.csv.gz"
MANIFEST = ROOT / "cloud_data" / "manifests" / "jnu_intraday_path_jpn225_spy_public_holdout_g2.json"
JPN_URL = "https://raw.githubusercontent.com/getdata-finance/jpn225-1m-ohlcv-index-historical-data/main/JPN225_1m.csv"
SPY_URL = "https://query1.finance.yahoo.com/v8/finance/chart/SPY?period1=1767225600&period2=1785628800&interval=1d&events=history&includeAdjustedClose=true"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 JerryBacktestLab-PathG2/1.0", "Accept": "application/json,text/csv,*/*"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def build_japan_targets(raw: bytes) -> pd.DataFrame:
    d = pd.read_csv(io.BytesIO(raw))
    d["datetime"] = pd.to_datetime(d["datetime"], utc=True, errors="coerce")
    d["close"] = pd.to_numeric(d["close"], errors="coerce")
    d = d.dropna(subset=["datetime", "close"]).sort_values("datetime").set_index("datetime")
    d.index = d.index.tz_convert("Asia/Tokyo")
    d["trade_date"] = pd.Index(d.index.date)
    mins = d.index.hour * 60 + d.index.minute
    first = d[(mins >= 9 * 60) & (mins < 9 * 60 + 30)].copy()
    last = d[(mins >= 14 * 60 + 30) & (mins < 15 * 60)].copy()
    rows = []
    dates = sorted(set(first.trade_date).intersection(set(last.trade_date)))
    for date in dates:
        a = first[first.trade_date == date].sort_index()
        b = last[last.trade_date == date].sort_index()
        if len(a) < 25 or len(b) < 25:
            continue
        first_ret = float(math.log(float(a.close.iloc[-1]) / float(a.close.iloc[0])))
        last_ret = float(math.log(float(b.close.iloc[-1]) / float(b.close.iloc[0])))
        rows.append({"trade_date": pd.Timestamp(date), "first30_return": first_ret, "last30_return": last_ret, "first30_bars": int(len(a)), "last30_bars": int(len(b))})
    out = pd.DataFrame(rows).set_index("trade_date").sort_index()
    if out.empty:
        raise RuntimeError("no complete Japan target days")
    return out


def build_spy_returns(raw: bytes) -> pd.DataFrame:
    obj = json.loads(raw)
    r = obj["chart"]["result"][0]
    ts = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("America/New_York")
    q = r["indicators"]["quote"][0]
    d = pd.DataFrame({"date": pd.Index(ts.date), "close": pd.to_numeric(q["close"], errors="coerce")}).dropna()
    d = d.drop_duplicates("date", keep="last").sort_values("date")
    d["spy_return"] = np.log(d.close).diff()
    d["date"] = pd.to_datetime(d["date"])
    return d.dropna(subset=["spy_return"]).set_index("date")[["spy_return"]]


def causal_join(targets: pd.DataFrame, spy: pd.DataFrame) -> pd.DataFrame:
    sdates = spy.index.to_numpy()
    vals = spy.spy_return.to_numpy(float)
    pred = []
    pred_date = []
    for d in targets.index:
        pos = np.searchsorted(sdates, np.datetime64(d), side="left") - 1
        if pos < 0:
            pred.append(np.nan); pred_date.append(pd.NaT)
        else:
            pred.append(float(vals[pos])); pred_date.append(pd.Timestamp(sdates[pos]))
    out = targets.copy()
    out["prior_spy_return"] = pred
    out["prior_spy_date"] = pred_date
    return out.dropna(subset=["prior_spy_return"])


def expanding_eval(d: pd.DataFrame, target_col: str, min_train: int) -> pd.DataFrame:
    rows = []
    for i in range(min_train, len(d)):
        train = d.iloc[:i].dropna(subset=[target_col, "prior_spy_return"])
        row = d.iloc[i]
        if len(train) < min_train:
            continue
        x = train.prior_spy_return.to_numpy(float)
        y = train[target_col].to_numpy(float)
        X = np.c_[np.ones(len(x)), x]
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        pred = float(beta[0] + beta[1] * float(row.prior_spy_return))
        base = float(np.mean(y))
        rows.append({"trade_date": d.index[i], "actual": float(row[target_col]), "pred": pred, "baseline": base, "beta": float(beta[1])})
    return pd.DataFrame(rows).set_index("trade_date") if rows else pd.DataFrame()


def bootstrap(x: pd.Series, block: int, samples: int, seed: int) -> dict:
    v = x.dropna().to_numpy(float); n = len(v)
    if n < 20:
        return {"n": n, "mean": float(v.mean()) if n else None, "prob_positive": None, "ci95": None}
    block = max(1, min(block, n)); starts = np.arange(n - block + 1); rng = np.random.default_rng(seed); means = []
    for _ in range(samples):
        z = []
        while len(z) < n:
            s = int(rng.choice(starts)); z.extend(v[s:s + block])
        means.append(float(np.mean(z[:n])))
    lo, hi = np.quantile(means, [0.025, 0.975])
    return {"n": n, "mean": float(v.mean()), "prob_positive": float(np.mean(np.asarray(means) > 0)), "ci95": [float(lo), float(hi)]}


def one_cell(d: pd.DataFrame, target: str, expected_sign: str, cfg: dict) -> tuple[dict, pd.DataFrame]:
    fc = expanding_eval(d, target, int(cfg["minimum_training_days"]))
    if fc.empty:
        return {"status": "DATA_INCONCLUSIVE_TOO_FEW_OOS_DAYS", "oos_days": 0}, fc
    base_loss = (fc.actual - fc.baseline) ** 2
    model_loss = (fc.actual - fc.pred) ** 2
    diff = base_loss - model_loss
    bcfg = cfg["block_bootstrap"]
    bs = bootstrap(diff, int(bcfg["block_days"]), int(bcfg["samples"]), int(bcfg["seed"]))
    base_hit = float((np.sign(fc.baseline) == np.sign(fc.actual)).mean())
    model_hit = float((np.sign(fc.pred) == np.sign(fc.actual)).mean())
    final_beta = float(fc.beta.iloc[-1]); sign_ok = final_beta < 0 if expected_sign == "negative" else final_beta > 0
    pprob = bs.get("prob_positive")
    gate = bool(sign_ok and float(diff.mean()) > 0 and pprob is not None and pprob >= 0.95 and model_hit >= base_hit)
    return {
        "status": "CELL_PASS" if gate else "CELL_FAIL_CURRENT_PROXY_SPEC",
        "oos_days": int(len(fc)), "oos_from": str(fc.index.min().date()), "oos_to": str(fc.index.max().date()),
        "expected_beta_sign": expected_sign, "final_expanding_beta": final_beta, "median_expanding_beta": float(fc.beta.median()), "coefficient_sign_ok": bool(sign_ok),
        "baseline_mse": float(base_loss.mean()), "model_mse": float(model_loss.mean()), "mse_improvement": float(diff.mean()), "mse_bootstrap": bs,
        "baseline_sign_accuracy": base_hit, "model_sign_accuracy": model_hit, "sign_accuracy_not_worse": bool(model_hit >= base_hit),
        "one_sided_p": None if pprob is None else float(1.0 - pprob)
    }, fc


def holm_two(cells: dict, alpha: float) -> dict:
    items = [(k, v.get("one_sided_p")) for k, v in cells.items()]
    if any(p is None for _, p in items):
        return {"pass": False, "reason": "missing p-value"}
    ordered = sorted(items, key=lambda z: z[1])
    checks = []
    passed = True
    m = len(ordered)
    for i, (name, p) in enumerate(ordered):
        threshold = alpha / (m - i)
        ok = p <= threshold
        checks.append({"cell": name, "p": p, "threshold": threshold, "pass": ok})
        if not ok:
            passed = False
            break
    return {"pass": passed, "alpha": alpha, "method": "Holm", "checks": checks}


def main() -> None:
    prereg = json.loads(PREREG.read_text())
    jraw = fetch(JPN_URL); sraw = fetch(SPY_URL)
    targets = build_japan_targets(jraw); spy = build_spy_returns(sraw); panel = causal_join(targets, spy)
    cfg = prereg["oos"]
    first, ffc = one_cell(panel, "first30_return", "negative", cfg)
    last, lfc = one_cell(panel, "last30_return", "positive", cfg)
    cells = {"H1_FIRST30": first, "H2_LAST30": last}
    holm = holm_two(cells, float(cfg["family_correction"]["alpha"]))
    both = all(v.get("status") == "CELL_PASS" for v in cells.values())
    status = "PROXY_PATH_CURRENT_SAMPLE_CONSISTENT" if both and holm["pass"] else "PROXY_PATH_CURRENT_SAMPLE_NOT_CONFIRMED"
    derived = panel[["first30_return", "last30_return", "prior_spy_return", "prior_spy_date", "first30_bars", "last30_bars"]].copy()
    RESULT.parent.mkdir(parents=True, exist_ok=True); REPORT.parent.mkdir(parents=True, exist_ok=True); DERIVED.parent.mkdir(parents=True, exist_ok=True); MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    derived.to_csv(DERIVED, compression="gzip")
    result = {"candidate_id": prereg["candidate_id"], "status": status, "formal_true_jnu_status": "STILL_PENDING_TRUE_OSE", "promotion_power": "NONE_TO_TRUE_JNU", "panel_days": int(len(panel)), "cells": cells, "holm": holm, "source_sha256": {"jpn225": hashlib.sha256(jraw).hexdigest(), "spy_yahoo_transient": hashlib.sha256(sraw).hexdigest()}, "guardrail": "SPY and Japan225 are proxies; this result cannot rescue G0 or validate live JNU direction.", "generated_at_utc": datetime.now(timezone.utc).isoformat()}
    manifest = {"candidate_id": prereg["candidate_id"], "target_source": JPN_URL, "predictor_source": "Yahoo Finance chart/SPY daily (transient raw)", "raw_persisted_in_repo": False, "derived_path": str(DERIVED.relative_to(ROOT)), "derived_sha256": hashlib.sha256(DERIVED.read_bytes()).hexdigest(), "source_sha256": result["source_sha256"]}
    RESULT.write_text(json.dumps(result, indent=2) + "\n")
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    REPORT.write_text("# JNU intraday path JPN225/SPY public holdout G2\n\n" + f"- Status: **{status}**\n- Panel days: {len(panel)}\n- H1 FIRST30: {first.get('status')} / beta={first.get('final_expanding_beta')} / MSE P={first.get('mse_bootstrap',{}).get('prob_positive')}\n- H2 LAST30: {last.get('status')} / beta={last.get('final_expanding_beta')} / MSE P={last.get('mse_bootstrap',{}).get('prob_positive')}\n- Holm family pass: {holm.get('pass')}\n\nProxy-only current-regime stress test. It cannot replace true-OSE/JNU confirmation or erase the negative 2011-2018 proxy G0 result.\n")

if __name__ == "__main__":
    main()
