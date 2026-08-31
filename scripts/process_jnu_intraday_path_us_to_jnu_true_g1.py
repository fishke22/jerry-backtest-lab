from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "config" / "jnu_intraday_path_us_to_jnu_true_g1_prereg.json"
PANEL = ROOT / "cloud_data" / "derived" / "jnu_225labo_micro_intraday_path_v1.csv"
MANIFEST = ROOT / "cloud_data" / "manifests" / "jnu_225labo_micro_intraday_path_v1_manifest.json"
RESULT = ROOT / "intraday_path_results" / "jnu_intraday_path_us_to_jnu_true_g1.json"
REPORT = ROOT / "intraday_path_reports" / "jnu_intraday_path_us_to_jnu_true_g1.md"

KAGGLE_URL = "https://www.kaggle.com/api/v1/datasets/download/paveljurke/s-and-p-500-gspc-historical-data?datasetVersionNumber=732"
KAGGLE_ZIP_SHA = "8f19fafb398ad048776340152bac5e9129f74c6646ea0ec76b1961e6a72ce521"
SPX_MEMBER = "sap500.csv"
SPX_CSV_SHA = "0686d640b1653bab8482905c419b7b799cce578825e9e866eeec7a19169c2f66"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 JerryBacktestLab-TrueJNUPathG1/1.0", "Accept": "*/*"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def load_spx_returns(prereg: dict) -> tuple[pd.DataFrame, dict]:
    zraw = fetch_bytes(KAGGLE_URL)
    if sha256_bytes(zraw) != KAGGLE_ZIP_SHA:
        raise RuntimeError("fail closed: pinned Kaggle ZIP SHA-256 mismatch")
    with zipfile.ZipFile(io.BytesIO(zraw)) as zf:
        raw = zf.read(SPX_MEMBER)
    if sha256_bytes(raw) != SPX_CSV_SHA:
        raise RuntimeError("fail closed: pinned sap500.csv SHA-256 mismatch")

    d = pd.read_csv(io.BytesIO(raw))
    if not {"Date", "Close"}.issubset(d.columns):
        raise RuntimeError("fail closed: SPX source schema changed")
    d["date"] = pd.to_datetime(d["Date"], errors="coerce")
    d["close"] = pd.to_numeric(d["Close"], errors="coerce")
    d = d.dropna(subset=["date", "close"]).sort_values("date").drop_duplicates("date", keep="last")
    d["prior_spx_return"] = np.log(d["close"]).diff()
    d = d.dropna(subset=["prior_spx_return"]).set_index("date")[["prior_spx_return"]]
    meta = {
        "dataset": prereg["data"]["predictor"]["source"],
        "dataset_version": prereg["data"]["predictor"]["dataset_version"],
        "license_label": prereg["data"]["predictor"]["license_label"],
        "zip_sha256": KAGGLE_ZIP_SHA,
        "csv_sha256": SPX_CSV_SHA,
        "spx_first_return_date": str(d.index.min().date()),
        "spx_last_return_date": str(d.index.max().date()),
        "raw_persisted_in_repo": False,
    }
    return d, meta


def load_jnu_panel() -> tuple[pd.DataFrame, dict]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("raw_data_cloud_uploaded") is not False:
        raise RuntimeError("fail closed: raw_data_cloud_uploaded must be false")
    if manifest.get("critical_data_quality_issues"):
        raise RuntimeError("fail closed: unresolved JNU path critical DQ issues")
    if manifest.get("derived_output_hash") != sha256_file(PANEL):
        raise RuntimeError("fail closed: JNU path panel hash mismatch")
    d = pd.read_csv(PANEL)
    required = {
        "trading_date", "first30_return", "middle_return", "last30_return",
        "day_session_return", "first30_bars", "middle_bars", "last30_bars",
    }
    if not required.issubset(d.columns):
        raise RuntimeError(f"fail closed: missing JNU path columns {sorted(required-set(d.columns))}")
    d["trading_date"] = pd.to_datetime(d["trading_date"], errors="coerce")
    for c in ["first30_return", "middle_return", "last30_return", "day_session_return"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["trading_date", "first30_return", "middle_return", "last30_return"])
    d = d.sort_values("trading_date").drop_duplicates("trading_date", keep="last").set_index("trading_date")
    return d, manifest


def causal_join(jnu: pd.DataFrame, spx: pd.DataFrame) -> pd.DataFrame:
    sdates = spx.index.to_numpy()
    vals = spx["prior_spx_return"].to_numpy(float)
    pvals = []
    pdates = []
    for d in jnu.index:
        pos = np.searchsorted(sdates, np.datetime64(d), side="left") - 1
        if pos < 0:
            pvals.append(np.nan)
            pdates.append(pd.NaT)
        else:
            pvals.append(float(vals[pos]))
            pdates.append(pd.Timestamp(sdates[pos]))
    out = jnu.copy()
    out["prior_spx_return"] = pvals
    out["prior_spx_date"] = pdates
    return out.dropna(subset=["prior_spx_return"])


def block_bootstrap(values: pd.Series, block: int, samples: int, seed: int) -> dict:
    x = values.dropna().to_numpy(float)
    n = len(x)
    if n < 20:
        return {"n": n, "mean": float(np.mean(x)) if n else None, "prob_positive": None, "ci95": None}
    block = max(1, min(block, n))
    starts = np.arange(n - block + 1)
    rng = np.random.default_rng(seed)
    means = np.empty(samples, dtype=float)
    for i in range(samples):
        z = []
        while len(z) < n:
            s = int(rng.choice(starts))
            z.extend(x[s:s+block])
        means[i] = float(np.mean(z[:n]))
    lo, hi = np.quantile(means, [0.025, 0.975])
    return {
        "n": n,
        "mean": float(np.mean(x)),
        "prob_positive": float(np.mean(means > 0)),
        "ci95": [float(lo), float(hi)],
    }


def expanding_cell(d: pd.DataFrame, target: str, expected_sign: str, min_train: int) -> pd.DataFrame:
    rows = []
    for i in range(min_train, len(d)):
        train = d.iloc[:i].dropna(subset=[target, "prior_spx_return"])
        row = d.iloc[i]
        if len(train) < min_train:
            continue
        x = train["prior_spx_return"].to_numpy(float)
        y = train[target].to_numpy(float)
        X = np.c_[np.ones(len(x)), x]
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        pred = float(beta[0] + beta[1] * float(row["prior_spx_return"]))
        base = float(np.mean(y))
        rows.append({
            "trade_date": d.index[i],
            "actual": float(row[target]),
            "pred": pred,
            "baseline": base,
            "beta": float(beta[1]),
        })
    return pd.DataFrame(rows).set_index("trade_date") if rows else pd.DataFrame()


def evaluate_cell(d: pd.DataFrame, target: str, expected_sign: str, cfg: dict) -> tuple[dict,pd.DataFrame]:
    fc = expanding_cell(d, target, expected_sign, int(cfg["minimum_training_days"]))
    if fc.empty:
        return {"status":"DATA_INCONCLUSIVE_TOO_FEW_OOS_DAYS","oos_days":0}, fc
    base_loss = (fc["actual"] - fc["baseline"])**2
    model_loss = (fc["actual"] - fc["pred"])**2
    diff = base_loss - model_loss
    bcfg = cfg["block_bootstrap"]
    bs = block_bootstrap(diff, int(bcfg["block_days"]), int(bcfg["samples"]), int(bcfg["seed"]))
    base_hit = float((np.sign(fc["baseline"]) == np.sign(fc["actual"])).mean())
    model_hit = float((np.sign(fc["pred"]) == np.sign(fc["actual"])).mean())
    final_beta = float(fc["beta"].iloc[-1])
    sign_ok = final_beta < 0 if expected_sign == "negative" else final_beta > 0
    pprob = bs.get("prob_positive")
    gate = bool(sign_ok and float(diff.mean()) > 0 and pprob is not None and pprob >= 0.95 and model_hit >= base_hit)
    recent = diff.loc[diff.index >= pd.Timestamp("2024-11-05")]
    return {
        "status":"CELL_PASS" if gate else "CELL_FAIL_TRUE_JNU_CURRENT_SPEC",
        "target":target,
        "expected_beta_sign":expected_sign,
        "oos_days":int(len(fc)),
        "oos_from":str(fc.index.min().date()),
        "oos_to":str(fc.index.max().date()),
        "final_expanding_beta":final_beta,
        "median_expanding_beta":float(fc["beta"].median()),
        "coefficient_sign_ok":bool(sign_ok),
        "baseline_mse":float(base_loss.mean()),
        "model_mse":float(model_loss.mean()),
        "mse_improvement":float(diff.mean()),
        "mse_bootstrap":bs,
        "baseline_sign_accuracy":base_hit,
        "model_sign_accuracy":model_hit,
        "sign_accuracy_not_worse":bool(model_hit >= base_hit),
        "one_sided_p":None if pprob is None else float(1.0-pprob),
        "recent_post_2024_11_05_mse_improvement":float(recent.mean()) if len(recent) else None,
    }, fc


STATE_COLS = ["first30_return","middle_return","last30_return"]
STATE_NAMES = ["FIRST30","MIDDLE","LAST30"]


def universal_design(x: np.ndarray, states: np.ndarray) -> np.ndarray:
    n=len(x)
    dummies=np.zeros((n,3),float)
    for i,s in enumerate(states):
        dummies[i,s]=1.0
    return np.c_[dummies, x]


def interaction_design(x: np.ndarray, states: np.ndarray) -> np.ndarray:
    n=len(x)
    dummies=np.zeros((n,3),float)
    slopes=np.zeros((n,3),float)
    for i,s in enumerate(states):
        dummies[i,s]=1.0
        slopes[i,s]=x[i]
    return np.c_[dummies, slopes]


def long_train(d: pd.DataFrame) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    ys=[]; xs=[]; states=[]
    for _,r in d.iterrows():
        x=float(r["prior_spx_return"])
        for si,col in enumerate(STATE_COLS):
            ys.append(float(r[col])); xs.append(x); states.append(si)
    return np.asarray(ys,float),np.asarray(xs,float),np.asarray(states,int)


def evaluate_h3(d: pd.DataFrame, cfg: dict) -> tuple[dict,pd.DataFrame]:
    min_train=int(cfg["minimum_training_days"])
    rows=[]
    for i in range(min_train,len(d)):
        train=d.iloc[:i].dropna(subset=STATE_COLS+["prior_spx_return"])
        row=d.iloc[i]
        if len(train)<min_train:
            continue
        y,x,states=long_train(train)
        bu,*_=np.linalg.lstsq(universal_design(x,states),y,rcond=None)
        bi,*_=np.linalg.lstsq(interaction_design(x,states),y,rcond=None)
        x0=float(row["prior_spx_return"])
        y0=np.asarray([float(row[c]) for c in STATE_COLS],float)
        st=np.asarray([0,1,2],int)
        xx=np.asarray([x0,x0,x0],float)
        pu=universal_design(xx,st)@bu
        pi=interaction_design(xx,st)@bi
        mse_u=float(np.mean((y0-pu)**2))
        mse_i=float(np.mean((y0-pi)**2))
        rows.append({
            "trade_date":d.index[i],
            "universal_mse":mse_u,
            "interaction_mse":mse_i,
            "mse_improvement":mse_u-mse_i,
            "beta_first":float(bi[3]),
            "beta_middle":float(bi[4]),
            "beta_last":float(bi[5]),
        })
    fc=pd.DataFrame(rows).set_index("trade_date") if rows else pd.DataFrame()
    if fc.empty:
        return {"status":"DATA_INCONCLUSIVE_TOO_FEW_OOS_DAYS","oos_days":0},fc
    bcfg=cfg["block_bootstrap"]
    bs=block_bootstrap(fc["mse_improvement"],int(bcfg["block_days"]),int(bcfg["samples"]),int(bcfg["seed"]))
    pprob=bs.get("prob_positive")
    gate=bool(float(fc["mse_improvement"].mean())>0 and pprob is not None and pprob>=0.95)
    recent=fc.loc[fc.index>=pd.Timestamp("2024-11-05"),"mse_improvement"]
    return {
        "status":"CELL_PASS" if gate else "CELL_FAIL_TRUE_JNU_CURRENT_SPEC",
        "oos_days":int(len(fc)),
        "oos_from":str(fc.index.min().date()),
        "oos_to":str(fc.index.max().date()),
        "universal_mse":float(fc["universal_mse"].mean()),
        "interaction_mse":float(fc["interaction_mse"].mean()),
        "mse_improvement":float(fc["mse_improvement"].mean()),
        "mse_bootstrap":bs,
        "one_sided_p":None if pprob is None else float(1.0-pprob),
        "final_state_betas":{
            "FIRST30":float(fc["beta_first"].iloc[-1]),
            "MIDDLE":float(fc["beta_middle"].iloc[-1]),
            "LAST30":float(fc["beta_last"].iloc[-1]),
        },
        "recent_post_2024_11_05_mse_improvement":float(recent.mean()) if len(recent) else None,
    },fc


def holm(cells: dict, alpha: float) -> dict:
    items=[(k,v.get("one_sided_p")) for k,v in cells.items()]
    if any(p is None for _,p in items):
        return {"pass":False,"reason":"missing p-value","method":"Holm","alpha":alpha}
    ordered=sorted(items,key=lambda z:z[1])
    checks=[]
    passed=True
    m=len(ordered)
    for i,(name,p) in enumerate(ordered):
        thr=alpha/(m-i)
        ok=bool(p<=thr)
        checks.append({"cell":name,"p":float(p),"threshold":float(thr),"pass":ok})
        if not ok:
            passed=False
            break
    return {"pass":passed,"method":"Holm","alpha":alpha,"checks":checks}


def main()->None:
    prereg=json.loads(PREREG.read_text(encoding="utf-8"))
    jnu,manifest=load_jnu_panel()
    spx,spx_meta=load_spx_returns(prereg)
    panel=causal_join(jnu,spx)
    cfg=prereg["oos"]

    h1,h1fc=evaluate_cell(panel,"first30_return","negative",cfg)
    h2,h2fc=evaluate_cell(panel,"last30_return","positive",cfg)
    h3,h3fc=evaluate_h3(panel,cfg)
    cells={"H1_FIRST30":h1,"H2_LAST30":h2,"H3_STATE_INTERACTION":h3}
    hc=holm(cells,float(cfg["family_correction"]["alpha"]))
    all_pass=all(v.get("status")=="CELL_PASS" for v in cells.values())
    status="TRUE_JNU_INTRADAY_PATH_INFORMATION_PASS" if all_pass and hc["pass"] else "REJECT_TRUE_JNU_CURRENT_SPEC"

    result={
        "candidate_id":prereg["candidate_id"],
        "status":status,
        "source_role":"EXACT_PRODUCT_TRUE_JNU_INFORMATION_TEST",
        "promotion_power":"INFORMATION_GATE_ONLY_NOT_AUTOMATIC_TRADING_ALPHA",
        "panel_days_before_alignment":int(len(jnu)),
        "panel_days_after_causal_spx_alignment":int(len(panel)),
        "aligned_from":str(panel.index.min().date()) if len(panel) else None,
        "aligned_to":str(panel.index.max().date()) if len(panel) else None,
        "spx_source":spx_meta,
        "jnu_derived_panel_sha256":sha256_file(PANEL),
        "jnu_manifest_sha256":sha256_file(MANIFEST),
        "cells":cells,
        "holm":hc,
        "next_rule":(
            "Only if PASS: preregister a concrete trading-rule translation and proceed through applicable cost/overfit/holdout stages."
            if status=="TRUE_JNU_INTRADAY_PATH_INFORMATION_PASS"
            else "Current true-JNU specification is rejected. Do not tune windows, switch predictor class, drop cells, or add indicators to rescue it."
        ),
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
    }

    RESULT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(
        "# True-JNU prior-SPX intraday path G1\n\n"
        f"- Status: **{status}**\n"
        f"- Causal aligned days: {len(panel)} ({result['aligned_from']} → {result['aligned_to']})\n"
        f"- H1 FIRST30: {h1.get('status')} / beta={h1.get('final_expanding_beta')} / MSE P={h1.get('mse_bootstrap',{}).get('prob_positive')}\n"
        f"- H2 LAST30: {h2.get('status')} / beta={h2.get('final_expanding_beta')} / MSE P={h2.get('mse_bootstrap',{}).get('prob_positive')}\n"
        f"- H3 state interaction: {h3.get('status')} / MSE P={h3.get('mse_bootstrap',{}).get('prob_positive')}\n"
        f"- Holm family pass: {hc.get('pass')}\n\n"
        "Exact-product OSE JNU information test using the frozen FIRST30/MIDDLE/LAST30 definitions and pinned ^GSPC predictor source. "
        "A PASS would still require downstream trading/cost/overfit validation before live directional use.\n",
        encoding="utf-8",
    )
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
