from __future__ import annotations

import hashlib
import json
import math
import time
import traceback
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REQUESTS = ROOT / "dpd_requests"
RESULTS = ROOT / "dpd_results"
REPORTS = ROOT / "dpd_reports"
CACHE = ROOT / ".cache" / "market-data"

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
SYMBOLS = {
    "NIY": "NIY=F",
    "NKD": "NKD=F",
    "ES": "ES=F",
    "NQ": "NQ=F",
    "N225": "^N225",
}

def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def fetch_cached_json(symbol: str, interval: str, range_: str, force: bool) -> tuple[bytes, bool, str]:
    CACHE.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() else "_" for c in symbol)
    name = f"yahoo_{safe}_{interval}_{range_}.json"
    path = CACHE / name
    url = YAHOO_CHART.format(symbol=urllib.parse.quote(symbol, safe=""))
    url += "?" + urllib.parse.urlencode({
        "interval": interval,
        "range": range_,
        "includePrePost": "true",
        "events": "div,splits",
    })
    if path.exists() and not force:
        return path.read_bytes(), True, url
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 JerryBacktestLab/DPD-0.1",
                    "Accept": "application/json,text/plain,*/*",
                },
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            path.write_bytes(raw)
            return raw, False, url
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"fetch failed for {symbol}/{interval}: {last}")

def parse_chart(raw: bytes, name: str) -> tuple[pd.Series, dict]:
    obj = json.loads(raw.decode("utf-8"))
    chart = obj.get("chart", {})
    if chart.get("error"):
        raise RuntimeError(f"Yahoo chart error for {name}: {chart['error']}")
    result = chart.get("result") or []
    if not result:
        raise RuntimeError(f"Yahoo chart returned no result for {name}")
    r = result[0]
    ts = r.get("timestamp") or []
    quote = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    close = quote.get("close") or []
    if not ts or not close:
        raise RuntimeError(f"Yahoo chart missing timestamps/close for {name}")
    idx = pd.to_datetime(ts, unit="s", utc=True)
    s = pd.Series(close, index=idx, name=name, dtype="float64").dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    meta = r.get("meta") or {}
    return s, {
        "symbol": meta.get("symbol"),
        "exchange_name": meta.get("exchangeName"),
        "exchange_timezone": meta.get("exchangeTimezoneName"),
        "first_trade_date": meta.get("firstTradeDate"),
    }

def logret(s: pd.Series, interval_minutes: int) -> pd.Series:
    out = np.log(s).diff()
    gap = s.index.to_series().diff().dt.total_seconds()
    out[gap > interval_minutes * 60 + 30] = np.nan
    return out

def state_mask(index: pd.DatetimeIndex, state: str) -> np.ndarray:
    if state == "JP_CASH":
        z = index.tz_convert("Asia/Tokyo")
        mins = z.hour * 60 + z.minute
        return np.asarray(((mins >= 540) & (mins <= 690)) | ((mins >= 750) & (mins <= 930)))
    if state == "US_CASH":
        z = index.tz_convert("America/New_York")
        mins = z.hour * 60 + z.minute
        return np.asarray((mins >= 570) & (mins <= 960))
    raise ValueError(f"unknown state: {state}")

def aligned_returns(data: dict[str, pd.Series], names: list[str], interval_minutes: int) -> pd.DataFrame:
    parts = [logret(data[n], interval_minutes).rename(n) for n in names]
    return pd.concat(parts, axis=1, join="inner").dropna()

def lead_corr(df: pd.DataFrame, predictor: str, target: str, state: str, max_lag_bars: int) -> list[dict]:
    d = df.loc[state_mask(df.index, state), [predictor, target]].copy()
    rows = []
    for k in range(-max_lag_bars, max_lag_bars + 1):
        future_target = d[target].shift(-k)
        ok = d[predictor].notna() & future_target.notna()
        rows.append({
            "lead_bars": int(k),
            "predictor_leads_when_positive": True,
            "corr": float(d.loc[ok, predictor].corr(future_target.loc[ok])) if int(ok.sum()) > 2 else None,
            "n": int(ok.sum()),
        })
    return rows

def chronological_oos_increment(
    df: pd.DataFrame,
    target: str,
    predictor: str,
    state: str,
    train_fraction: float,
    interval_minutes: int,
) -> dict:
    d = df.loc[state_mask(df.index, state), [target, predictor]].copy()
    d["y"] = d[target].shift(-1)
    next_ts = d.index.to_series().shift(-1)
    d["contiguous"] = (next_ts - d.index.to_series()).dt.total_seconds().eq(interval_minutes * 60)
    d = d[d["contiguous"]].dropna()
    if len(d) < 100:
        return {"error": "insufficient_rows", "n": int(len(d))}
    utc_days = pd.Index(sorted(pd.unique(d.index.tz_convert("UTC").date)))
    cut = max(1, min(len(utc_days) - 1, int(math.floor(len(utc_days) * train_fraction))))
    train_days = set(utc_days[:cut])
    test_days = set(utc_days[cut:])
    train_mask = np.array([x in train_days for x in d.index.tz_convert("UTC").date])
    test_mask = np.array([x in test_days for x in d.index.tz_convert("UTC").date])
    tr = d.loc[train_mask]
    te = d.loc[test_mask]
    if len(tr) < 80 or len(te) < 20:
        return {
            "error": "insufficient_split",
            "n_train": int(len(tr)),
            "n_test": int(len(te)),
            "train_days": int(len(train_days)),
            "test_days": int(len(test_days)),
        }
    X0 = np.column_stack([np.ones(len(tr)), tr[target].to_numpy()])
    X1 = np.column_stack([np.ones(len(tr)), tr[target].to_numpy(), tr[predictor].to_numpy()])
    ytr = tr["y"].to_numpy()
    b0 = np.linalg.lstsq(X0, ytr, rcond=None)[0]
    b1 = np.linalg.lstsq(X1, ytr, rcond=None)[0]
    P0 = np.column_stack([np.ones(len(te)), te[target].to_numpy()]) @ b0
    P1 = np.column_stack([np.ones(len(te)), te[target].to_numpy(), te[predictor].to_numpy()]) @ b1
    y = te["y"].to_numpy()
    mse0 = float(np.mean((y - P0) ** 2))
    mse1 = float(np.mean((y - P1) ** 2))
    hit0 = float(np.mean(np.sign(P0) == np.sign(y)))
    hit1 = float(np.mean(np.sign(P1) == np.sign(y)))
    return {
        "n_train": int(len(tr)),
        "n_test": int(len(te)),
        "train_days": int(len(train_days)),
        "test_days": int(len(test_days)),
        "predictor_beta": float(b1[2]),
        "oos_mse_base": mse0,
        "oos_mse_full": mse1,
        "oos_mse_improvement_pct": float((mse0 - mse1) / mse0 * 100.0) if mse0 > 0 else 0.0,
        "oos_hit_base": hit0,
        "oos_hit_full": hit1,
        "oos_hit_delta_pp": float((hit1 - hit0) * 100.0),
    }

def strongest_nonzero_lead(rows: list[dict]) -> dict | None:
    eligible = [x for x in rows if x["lead_bars"] != 0 and x.get("corr") is not None]
    if not eligible:
        return None
    return max(eligible, key=lambda x: abs(float(x["corr"])))

def run_interval(request: dict, interval: str, range_: str) -> dict:
    interval_minutes = int(interval.rstrip("m"))
    force = bool(request.get("force_refresh", False))
    max_lag = int(request["max_lag_bars"])
    train_fraction = float(request["train_fraction"])
    date_to = pd.Timestamp(request["date_to"], tz="UTC") + pd.Timedelta(days=1)

    data: dict[str, pd.Series] = {}
    sources: dict[str, dict] = {}
    for name, symbol in SYMBOLS.items():
        raw, hit, url = fetch_cached_json(symbol, interval, range_, force)
        series, meta = parse_chart(raw, name)
        series = series[series.index < date_to]
        data[name] = series
        sources[name] = {
            "provider": "Yahoo Finance public chart endpoint",
            "source_class": "PROVISIONAL_PUBLIC_WEB_PROXY",
            "storage_class": "CACHE_ONLY",
            "symbol": symbol,
            "url": url,
            "sha256": sha256(raw),
            "cache_hit": bool(hit),
            "raw_committed": False,
            "rows_after_date_filter": int(len(series)),
            "first_timestamp_utc": str(series.index.min()) if len(series) else None,
            "last_timestamp_utc": str(series.index.max()) if len(series) else None,
            "provider_meta": meta,
        }

    cross = aligned_returns(data, ["NIY", "ES", "NQ"], interval_minutes)
    same_cme = aligned_returns(data, ["NIY", "NKD"], interval_minutes)
    cash = aligned_returns(data, ["NIY", "N225"], interval_minutes)

    out = {"interval": interval, "range": range_, "sources": sources, "states": {}}
    for state in ["JP_CASH", "US_CASH"]:
        pairs = [
            ("ES", "NIY", cross),
            ("NQ", "NIY", cross),
            ("NIY", "ES", cross),
        ]
        state_out = {}
        for predictor, target, df in pairs:
            corr = lead_corr(df, predictor, target, state, max_lag)
            state_out[f"{predictor}_to_{target}"] = {
                "lead_correlation": corr,
                "strongest_nonzero_lead": strongest_nonzero_lead(corr),
                "next_bar_oos_increment": chronological_oos_increment(
                    df, target, predictor, state, train_fraction, interval_minutes
                ),
            }
        out["states"][state] = state_out

    jp_same = {}
    for predictor, target, df in [
        ("NIY", "N225", cash),
        ("N225", "NIY", cash),
        ("NIY", "NKD", same_cme),
        ("NKD", "NIY", same_cme),
    ]:
        corr = lead_corr(df, predictor, target, "JP_CASH", max_lag)
        jp_same[f"{predictor}_to_{target}"] = {
            "lead_correlation": corr,
            "strongest_nonzero_lead": strongest_nonzero_lead(corr),
            "next_bar_oos_increment": chronological_oos_increment(
                df, target, predictor, "JP_CASH", train_fraction, interval_minutes
            ),
        }
    out["states"]["JP_SAME_UNDERLYING_PROXY"] = jp_same
    return out

def summarize(result: dict) -> dict:
    rows = []
    for interval_name, interval_data in result["interval_results"].items():
        for state, pairs in interval_data["states"].items():
            for pair, payload in pairs.items():
                lead = payload.get("strongest_nonzero_lead") or {}
                oos = payload.get("next_bar_oos_increment") or {}
                rows.append({
                    "interval": interval_name,
                    "state": state,
                    "pair": pair,
                    "lead_bars": lead.get("lead_bars"),
                    "lead_corr": lead.get("corr"),
                    "oos_mse_improvement_pct": oos.get("oos_mse_improvement_pct"),
                    "oos_hit_delta_pp": oos.get("oos_hit_delta_pp"),
                    "test_days": oos.get("test_days"),
                })
    return {
        "comparison_rows": rows,
        "promotion_gate": {
            "passes": False,
            "reason": "Required OSE and SGX venue-specific intraday data are absent. This run is a cloud pilot only.",
            "required_before_validation": [
                "OSE Nikkei 225 micro/mini/large contract-specific intraday data",
                "SGX Nikkei 225 contract-specific intraday data",
                "same-expiry identity alignment",
                "licensed/approved storage classification",
                "walk-forward and cost-aware EV validation",
                "multiple-testing controls and recent-regime stability",
            ],
        },
    }

def report_md(result: dict) -> str:
    lines = [
        f"# JNU Dynamic Price Discovery Cloud Pilot — {result['request_id']}",
        "",
        f"- Status: **{result['promotion_status']}**",
        "- Execution: GitHub Actions cloud runner",
        "- Raw downloads: GitHub Actions cloud cache only; not committed",
        "- Formal validation: **NOT ALLOWED** because OSE/SGX venue-specific intraday data are not present",
        "",
        "## Fixed preregistered design",
        f"- Intervals: {', '.join(result['request']['intervals'].keys())}",
        f"- Maximum lead/lag: ±{result['request']['max_lag_bars']} bars",
        f"- Chronological train fraction: {result['request']['train_fraction']:.0%}",
        "- States: JP_CASH and US_CASH",
        "- No post-hoc lag-window widening in this run",
        "",
        "## Comparison summary",
    ]
    for x in result["summary"]["comparison_rows"]:
        lc = "n/a" if x["lead_corr"] is None else f"{x['lead_corr']:.4f}"
        mi = "n/a" if x["oos_mse_improvement_pct"] is None else f"{x['oos_mse_improvement_pct']:.3f}%"
        hd = "n/a" if x["oos_hit_delta_pp"] is None else f"{x['oos_hit_delta_pp']:.3f}pp"
        lines.append(
            f"- {x['interval']} / {x['state']} / {x['pair']}: "
            f"strongest nonzero lead={x['lead_bars']} bars, corr={lc}, "
            f"OOS MSE Δ={mi}, hit Δ={hd}, test_days={x['test_days']}"
        )
    lines += [
        "",
        "## Interpretation guardrail",
        "- Same-bar correlation is not treated as a tradable lead.",
        "- A positive one-bar association is not promoted unless it survives longer OOS, costs, venue alignment, and multiple-testing gates.",
        "- Yahoo symbols are provisional public-web proxies, not authoritative OSE/SGX contract data.",
        "",
        "## Promotion gate",
        f"- PASS: **{result['summary']['promotion_gate']['passes']}**",
        f"- Reason: {result['summary']['promotion_gate']['reason']}",
        "",
    ]
    return "\n".join(lines)

def process(path: Path) -> None:
    rid = path.stem
    out_json = RESULTS / f"{rid}.json"
    out_md = REPORTS / f"{rid}.md"
    if out_json.exists():
        print(f"skip {rid}: result exists")
        return
    request = json.loads(path.read_text(encoding="utf-8"))
    if request.get("request_id") != rid:
        raise ValueError("request_id must match filename stem")
    interval_results = {}
    for interval, cfg in request["intervals"].items():
        interval_results[interval] = run_interval(request, interval, str(cfg["range"]))
    result = {
        "request_id": rid,
        "status": "complete",
        "candidate_id": "DYNAMIC_PRICE_DISCOVERY",
        "promotion_status": "PILOT_ONLY_INSUFFICIENT_VENUE_COVERAGE",
        "request": request,
        "interval_results": interval_results,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    result["summary"] = summarize(result)
    RESULTS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(report_md(result), encoding="utf-8")
    print(f"completed {rid}")

def main() -> int:
    REQUESTS.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    failures = []
    for path in sorted(REQUESTS.glob("*.json")):
        try:
            process(path)
        except Exception as exc:
            failures.append((path.name, str(exc)))
            traceback.print_exc()
    if failures:
        print(json.dumps({"failures": failures}, ensure_ascii=False))
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
