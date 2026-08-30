from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from process_phase4b_evidence import (
    ROOT,
    _gdelt_timeline_adaptive,
    asof_strict,
    block_bootstrap_mean,
    expanding_ols_predict,
    holm_from_tail_probs,
    load_market,
    qlike,
)

REQUESTS = ROOT / "news_language_g1_requests"
RESULTS = ROOT / "news_language_g1_results"
REPORTS = ROOT / "news_language_g1_reports"
DERIVED = ROOT / "cloud_data" / "derived"
MANIFESTS = ROOT / "cloud_data" / "manifests"


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def quarter_windows(start: str, end: str) -> list[tuple[str, str]]:
    s = pd.to_datetime(start, format="%Y%m%d%H%M%S")
    e = pd.to_datetime(end, format="%Y%m%d%H%M%S")
    if not (pd.notna(s) and pd.notna(e) and s < e):
        raise ValueError(f"invalid interval {start}->{end}")
    out = []
    cursor = s
    first = True
    while cursor < e:
        month = ((cursor.month - 1) // 3 + 1) * 3 + 1
        year = cursor.year
        if month > 12:
            month = 1
            year += 1
        stop = min(pd.Timestamp(year=year, month=month, day=1), e)
        begin = cursor if first else cursor - pd.Timedelta(seconds=1)
        out.append((begin.strftime("%Y%m%d%H%M%S"), stop.strftime("%Y%m%d%H%M%S")))
        cursor = stop
        first = False
    return out


def gdelt_quarter_timeline(query: str, mode: str, start: str, end: str, key: str, force: bool) -> pd.Series:
    parts = []
    for i, (a, b) in enumerate(quarter_windows(start, end), start=1):
        cache = f"g1_{key}_{mode.lower()}_q{i}_{a[:8]}_{b[:8]}.json"
        part = _gdelt_timeline_adaptive(query, mode, a, b, cache, force)
        parts.append(part)
        print(f"g1 chunk ready: {key} {mode} {a[:8]}->{b[:8]}", flush=True)
    if not parts:
        raise RuntimeError(f"no GDELT data for {key} {mode}")
    out = pd.concat(parts).groupby(level=0).mean().sort_index()
    out.name = mode
    return out


def build_cell_features(query: str, close_index: pd.DatetimeIndex, req: dict, key: str) -> tuple[pd.DataFrame,pd.DataFrame]:
    start = pd.Timestamp(req["date_from"]).strftime("%Y%m%d000000")
    end = (pd.Timestamp(req["date_to"]) + pd.Timedelta(days=1)).strftime("%Y%m%d000000")
    force = bool(req.get("force_refresh", False))
    tone = gdelt_quarter_timeline(query, "TimelineTone", start, end, key, force)
    vol = gdelt_quarter_timeline(query, "TimelineVol", start, end, key, force)

    raw_daily = pd.DataFrame({"tone": tone, "volume": vol}).sort_index()
    raw_daily["abs_tone"] = raw_daily["tone"].abs()
    raw_daily["tone_ewm"] = raw_daily["tone"].ewm(
        halflife=float(req["news"]["half_life_days"]), adjust=False
    ).mean()

    aligned = pd.DataFrame(index=close_index)
    for col in raw_daily.columns:
        aligned[col] = asof_strict(close_index, raw_daily[col])
    return raw_daily, aligned


def evaluate(close: pd.Series, req: dict) -> tuple[dict,pd.DataFrame]:
    r = close.pct_change()
    var = r.pow(2)
    eps = 1e-10

    X0 = pd.DataFrame(index=close.index)
    X0["logv1"] = np.log(var.shift(1) + eps)
    X0["logv5"] = np.log(var.shift(1).rolling(5).mean() + eps)
    X0["logv22"] = np.log(var.shift(1).rolling(22).mean() + eps)

    ylog = np.log(var + eps)
    start = int(req["oos_start_days"])
    base_log = expanding_ols_predict(X0, ylog, start)
    base_var = np.exp(base_log)

    boot_cfg = req["bootstrap"]
    recent_days = int(req["recent_days"])
    threshold = float(req["news"]["min_bootstrap_qlike_improvement_probability"])
    categories = req["news"]["categories"]

    raw_results = {}
    tail_p = {}
    durable_parts = []

    for key, cell in categories.items():
        raw_daily, nf = build_cell_features(cell["query"], close.index, req, key)
        durable = raw_daily.add_prefix(f"{key}__")
        durable_parts.append(durable)

        X1 = pd.concat([X0, nf], axis=1)
        aug_log = expanding_ols_predict(X1, ylog, start)
        aug_var = np.exp(aug_log)

        df = pd.DataFrame({"actual":var, "base":base_var, "aug":aug_var}).dropna()
        q0 = qlike(df.actual, df.base)
        q1 = qlike(df.actual, df.aug)
        m0 = (df.actual-df.base)**2
        m1 = (df.actual-df.aug)**2
        qdiff = q0-q1
        mdiff = m0-m1

        bq = block_bootstrap_mean(
            qdiff, int(boot_cfg["block_days"]), int(boot_cfg["samples"]), int(boot_cfg["seed"])
        )
        bm = block_bootstrap_mean(
            mdiff, int(boot_cfg["block_days"]), int(boot_cfg["samples"]), int(boot_cfg["seed"])
        )
        tail_p[key] = max(0.0, 1.0-bq["prob_positive"])

        recent = df.tail(recent_days)
        rqdiff = qlike(recent.actual,recent.base)-qlike(recent.actual,recent.aug)
        rmdiff = (recent.actual-recent.base)**2-(recent.actual-recent.aug)**2

        raw_results[key] = {
            "query":cell["query"],
            "semantic_group":cell["semantic_group"],
            "source_language":cell["source_language"],
            "oos_days":int(len(df)),
            "qlike_improvement":float(qdiff.mean()),
            "mse_improvement":float(mdiff.mean()),
            "qlike_bootstrap":bq,
            "mse_bootstrap":bm,
            "recent_qlike_improvement":float(rqdiff.mean()),
            "recent_mse_improvement":float(rmdiff.mean()),
        }

    holm = holm_from_tail_probs(tail_p, float(req["news"]["holm_alpha"]))
    survivors = []
    for key,row in raw_results.items():
        checks = {
            "qlike_improves":row["qlike_improvement"]>0,
            "mse_improves":row["mse_improvement"]>0,
            "bootstrap_qlike":row["qlike_bootstrap"]["prob_positive"]>=threshold,
            "recent_qlike":row["recent_qlike_improvement"]>=0,
            "recent_mse":row["recent_mse_improvement"]>=0,
            "holm":bool(holm["reject"][key]),
        }
        row["checks"] = checks
        row["status"] = "NEWS_LANGUAGE_STATE_CANDIDATE" if all(checks.values()) else "FAIL_G1_CELL"
        if row["status"] == "NEWS_LANGUAGE_STATE_CANDIDATE":
            survivors.append(key)

    durable_panel = pd.concat(durable_parts,axis=1).sort_index()
    return {
        "source":"GDELT DOC 2.0 source-language filtered TimelineTone/TimelineVol",
        "categories":raw_results,
        "multiple_testing":holm,
        "survivors":survivors,
        "directional_trading_status":"PROHIBITED_G1",
        "session_status":"DEFERRED_TRUE_JNU_INTRADAY",
    }, durable_panel


def report(result: dict) -> str:
    n = result["news"]
    lines = [
        f"# JNU News Language/Source State G1 — {result['request_id']}",
        "",
        f"- Status: **{result['promotion_status']}**",
        f"- Survivors: {', '.join(n['survivors']) if n['survivors'] else 'NONE'}",
        "- Target role: next-day volatility/event-state only",
        "- Directional trading: prohibited in G1",
        "",
        "| Cell | Lang | QLIKE Δ | MSE Δ | Pboot QLIKE+ | Recent QLIKE Δ | Recent MSE Δ | Holm | Status |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for key,row in n["categories"].items():
        lines.append(
            f"| {key} | {row['source_language']} | {row['qlike_improvement']:.6g} | "
            f"{row['mse_improvement']:.6g} | {row['qlike_bootstrap']['prob_positive']:.3f} | "
            f"{row['recent_qlike_improvement']:.6g} | {row['recent_mse_improvement']:.6g} | "
            f"{row['checks']['holm']} | {row['status']} |"
        )
    lines += [
        "",
        "## Guardrails",
        "- Cell queries/languages were frozen before retrieval.",
        "- sourcelang filters original publication language; keyword matching uses GDELT English translations.",
        "- No cell may be dropped or merged post hoc.",
        "- A pass is a volatility/event-state candidate, not directional alpha.",
        "- Intraday session interaction requires true JNU data and a separate preregistration.",
        "",
    ]
    return "\n".join(lines)


def process(path: Path) -> None:
    req = json.loads(path.read_text(encoding="utf-8"))
    rid = path.stem
    if req.get("request_id") != rid:
        raise ValueError("request_id must match filename")

    RESULTS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    DERIVED.mkdir(parents=True,exist_ok=True)
    MANIFESTS.mkdir(parents=True,exist_ok=True)

    outj=RESULTS/f"{rid}.json"
    if outj.exists():
        print(f"skip {rid}: result exists")
        return

    close,_,_ = load_market(req)
    news,panel = evaluate(close,req)

    csv_bytes = gzip.compress(panel.to_csv(index=True).encode("utf-8"),compresslevel=9)
    datap = DERIVED/f"{rid}_news_panel.csv.gz"
    datap.write_bytes(csv_bytes)
    dsha = sha256(csv_bytes)

    manifest = {
        "dataset_id":"JNU_NEWS_LANGUAGE_SOURCE_G1_DAILY",
        "status":"DURABLE_DERIVED_NEWS_FEATURES",
        "date_from":req["date_from"],
        "date_to":req["date_to"],
        "cells":req["news"]["categories"],
        "features":["tone","volume","abs_tone","tone_ewm"],
        "source":"GDELT DOC 2.0",
        "source_language_semantics":"sourcelang filters original publication language; English-translated text is keyword searched.",
        "acquisition":"Quarter windows, single connection, pacing, cumulative cache, bounded adaptive split.",
        "raw_article_storage":"NONE",
        "path":str(datap.relative_to(ROOT)).replace("\\","/"),
        "sha256":dsha,
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
    }
    manp=MANIFESTS/f"{rid}_news_panel.json"
    manp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    result = {
        "request_id":rid,
        "candidate_id":"NEWS_STATE_LANGUAGE_SOURCE_G1",
        "status":"complete",
        "promotion_status":"INFORMATION_STATE_SCREEN_ONLY",
        "preregistration":req["preregistration"],
        "derived_dataset":str(datap.relative_to(ROOT)).replace("\\","/"),
        "derived_sha256":dsha,
        "manifest":str(manp.relative_to(ROOT)).replace("\\","/"),
        "news":news,
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
    }
    outj.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (REPORTS/f"{rid}.md").write_text(report(result),encoding="utf-8")
    print(f"completed {rid}")


def main()->int:
    REQUESTS.mkdir(exist_ok=True)
    failures=[]
    for p in sorted(REQUESTS.glob("*.json")):
        try:
            process(p)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            failures.append((p.name,str(exc)))
    if failures:
        print(json.dumps({"failures":failures},ensure_ascii=False))
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
