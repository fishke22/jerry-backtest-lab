from __future__ import annotations

import gzip
import hashlib
import io
import json
import time
import traceback
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REQUESTS = ROOT / "dataset_requests"
DATASET_DIR = ROOT / "cloud_data" / "derived"
MANIFEST_DIR = ROOT / "cloud_data" / "manifests"
REPORT_DIR = ROOT / "cloud_data" / "reports"
CACHE = ROOT / ".cache" / "market-data"

NIKKEI_FUTURES_CSV = (
    "https://indexes.nikkei.co.jp/nkave/historical/"
    "nikkei_225_futures_index_series_daily_en.csv"
)
FRED = (
    "https://fred.stlouisfed.org/graph/fredgraph.csv"
    "?id={series}&cosd={start}&coed={end}"
)
CBOE_VIX = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"

SERIES = {
    "NASDAQ100": {"provider":"FRED", "role":"US equity / NQ proxy"},
    "DEXJPUS": {"provider":"FRED", "role":"USDJPY conditional state"},
    "DGS2": {"provider":"FRED", "role":"US 2Y yield"},
    "DGS10": {"provider":"FRED", "role":"US 10Y yield"},
    "DCOILWTICO": {"provider":"FRED", "role":"WTI oil"},
    "DCOILBRENTEU": {"provider":"FRED", "role":"Brent oil"},
}

def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def fetch_cached(url: str, name: str, force: bool) -> tuple[bytes, bool]:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if path.exists() and not force:
        return path.read_bytes(), True
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent":"Mozilla/5.0 JerryBacktestLab/Dataset-0.1",
                    "Accept":"text/csv,*/*;q=0.8",
                },
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            path.write_bytes(raw)
            return raw, False
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"fetch failed for {name}: {last}")

def parse_generic_csv(raw: bytes, value_name: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
    if len(df.columns) < 2:
        raise RuntimeError(f"unexpected CSV shape for {value_name}")
    date_col = "DATE" if "DATE" in df.columns else (
        "observation_date" if "observation_date" in df.columns else df.columns[0]
    )
    val_col = value_name if value_name in df.columns else df.columns[-1]
    idx = pd.to_datetime(df[date_col], errors="coerce")
    val = pd.to_numeric(df[val_col], errors="coerce")
    s = pd.Series(val.to_numpy(), index=idx, name=value_name).dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()

def parse_nikkei(raw: bytes) -> pd.Series:
    df = pd.read_csv(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
    idx = pd.to_datetime(df.iloc[:,0], errors="coerce")
    val = pd.to_numeric(df.iloc[:,1], errors="coerce")
    s = pd.Series(val.to_numpy(), index=idx, name="NIKKEI_FUTURES_INDEX").dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()

def parse_vix(raw: bytes) -> pd.Series:
    df = pd.read_csv(io.StringIO(raw.decode("utf-8-sig", errors="replace")))
    cols = {str(x).strip().upper():x for x in df.columns}
    date_col = cols.get("DATE", df.columns[0])
    close_col = cols.get("CLOSE", df.columns[-1])
    idx = pd.to_datetime(df[date_col], errors="coerce")
    val = pd.to_numeric(df[close_col], errors="coerce")
    s = pd.Series(val.to_numpy(), index=idx, name="VIX").dropna()
    return s[~s.index.duplicated(keep="last")].sort_index()

def pct(s: pd.Series, periods: int = 1) -> pd.Series:
    return s.pct_change(periods, fill_method=None)

def zscore_lagged(s: pd.Series, window: int) -> pd.Series:
    mean = s.shift(1).rolling(window, min_periods=max(20, window//3)).mean()
    std = s.shift(1).rolling(window, min_periods=max(20, window//3)).std(ddof=0)
    return (s - mean) / std.replace(0, np.nan)

def build_features(levels: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=levels.index)

    # Target: durable derived returns, not the copyrighted raw level.
    nk = levels["NIKKEI_FUTURES_INDEX"]
    out["target_nikkei_fut_ret_1d"] = pct(nk,1)
    out["target_nikkei_fut_ret_5d"] = pct(nk,5)
    out["nikkei_rv20_lag1"] = out["target_nikkei_fut_ret_1d"].shift(1).rolling(20).std(ddof=0)
    out["nikkei_rv60_lag1"] = out["target_nikkei_fut_ret_1d"].shift(1).rolling(60).std(ddof=0)

    ndx = levels["NASDAQ100"]
    out["ndx_ret_1d_lag1"] = pct(ndx,1).shift(1)
    out["ndx_ret_5d_lag1"] = pct(ndx,5).shift(1)

    fx = levels["DEXJPUS"]
    out["usdjpy_ret_1d_lag1"] = pct(fx,1).shift(1)
    out["usdjpy_ret_5d_lag1"] = pct(fx,5).shift(1)

    y2 = levels["DGS2"]
    y10 = levels["DGS10"]
    out["us2y_change_bp_lag1"] = y2.diff().shift(1) * 100.0
    out["us10y_change_bp_lag1"] = y10.diff().shift(1) * 100.0
    out["us10y_2y_spread_bp_lag1"] = (y10-y2).shift(1) * 100.0

    wti = levels["DCOILWTICO"]
    brent = levels["DCOILBRENTEU"]
    out["wti_ret_1d_lag1"] = pct(wti,1).shift(1)
    out["brent_ret_1d_lag1"] = pct(brent,1).shift(1)

    vix = levels["VIX"]
    out["vix_ret_1d_lag1"] = pct(vix,1).shift(1)
    out["vix_level_z60_lag1"] = zscore_lagged(vix,60).shift(1)

    # Availability flags are useful for fail-closed research.
    for c in list(out.columns):
        out[f"avail__{c}"] = out[c].notna().astype("int8")

    return out

def process(path: Path) -> None:
    req = json.loads(path.read_text(encoding="utf-8"))
    rid = path.stem
    if req.get("request_id") != rid:
        raise ValueError("request_id must match filename stem")

    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    out_csv = DATASET_DIR / f"{rid}.csv.gz"
    out_manifest = MANIFEST_DIR / f"{rid}.json"
    out_report = REPORT_DIR / f"{rid}.md"
    if out_csv.exists() and out_manifest.exists():
        print(f"skip {rid}: durable dataset exists")
        return

    force = bool(req.get("force_refresh", False))
    start = str(req["date_from"])
    end = str(req["date_to"])

    source_meta = {}

    nk_raw, nk_hit = fetch_cached(NIKKEI_FUTURES_CSV, "nikkei_futures_daily.csv", force)
    nk = parse_nikkei(nk_raw)
    source_meta["NIKKEI_FUTURES_INDEX"] = {
        "provider":"Nikkei Indexes",
        "url":NIKKEI_FUTURES_CSV,
        "sha256":sha256(nk_raw),
        "cache_hit":nk_hit,
        "raw_storage":"CACHE_ONLY",
        "durable_output":"derived returns/features only",
    }

    data = {"NIKKEI_FUTURES_INDEX":nk}

    for series, meta in SERIES.items():
        url = FRED.format(series=series,start=start,end=end)
        raw, hit = fetch_cached(url, f"fred_{series.lower()}.csv", force)
        data[series] = parse_generic_csv(raw, series)
        source_meta[series] = {
            "provider":"FRED",
            "url":url,
            "sha256":sha256(raw),
            "cache_hit":hit,
            "raw_storage":"CACHE_ONLY",
            "durable_output":"derived features only",
            "role":meta["role"],
        }

    vix_raw, vix_hit = fetch_cached(CBOE_VIX, "cboe_vix_history.csv", force)
    data["VIX"] = parse_vix(vix_raw)
    source_meta["VIX"] = {
        "provider":"Cboe",
        "url":CBOE_VIX,
        "sha256":sha256(vix_raw),
        "cache_hit":vix_hit,
        "raw_storage":"CACHE_ONLY",
        "durable_output":"derived features only",
    }

    # Use the Nikkei target calendar. External values are point-in-time conservative:
    # same-date observations are shifted inside feature construction before prediction use.
    idx = data["NIKKEI_FUTURES_INDEX"].loc[start:end].index
    levels = pd.DataFrame(index=idx)
    for name,s in data.items():
        levels[name] = s.reindex(idx).ffill()

    features = build_features(levels)
    features = features.loc[start:end]
    features.index.name = "date"

    csv_bytes = features.to_csv(index=True).encode("utf-8")
    compressed = gzip.compress(csv_bytes, compresslevel=9)
    out_csv.write_bytes(compressed)
    dataset_sha = sha256(compressed)

    manifest = {
        "request_id":rid,
        "dataset_id":"JNU_CORE_DAILY_FEATURES_V1",
        "status":"DURABLE_DERIVED_CLOUD_DATASET",
        "date_from":start,
        "date_to":end,
        "rows":int(len(features)),
        "columns":list(features.columns),
        "dataset_sha256":dataset_sha,
        "dataset_path":str(out_csv.relative_to(ROOT)).replace("\\","/"),
        "sources":source_meta,
        "raw_data_policy":"Raw market downloads remain GitHub Actions cache only unless source-specific archival rights are approved.",
        "durable_data_policy":"Only derived research features plus provenance are committed to the private GitHub cloud repository.",
        "causal_timing":"External predictor features are lagged before use; target returns are not used as predictors without explicit lag.",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
    }
    out_manifest.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    lines = [
        f"# JNU Cloud Dataset Snapshot — {rid}",
        "",
        f"- Status: **{manifest['status']}**",
        f"- Rows: {manifest['rows']}",
        f"- Columns: {len(manifest['columns'])}",
        f"- Dataset SHA-256: `{dataset_sha}`",
        f"- Durable path: `{manifest['dataset_path']}`",
        "",
        "## Storage policy",
        "- Raw source downloads are cache-only unless archival rights are separately approved.",
        "- Derived features and provenance are durable in the private GitHub repository.",
        "- This dataset is intended to be reused by cloud backtests from mobile/ChatGPT control.",
        "",
        "## Sources",
    ]
    for name,m in source_meta.items():
        lines.append(f"- {name}: {m['provider']} | raw={m['raw_storage']} | sha256={m['sha256'][:16]}…")
    out_report.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"completed {rid}")

def main() -> int:
    REQUESTS.mkdir(exist_ok=True)
    failures=[]
    for p in sorted(REQUESTS.glob("*.json")):
        try:
            process(p)
        except Exception as exc:
            failures.append((p.name,str(exc)))
            traceback.print_exc()
    if failures:
        print(json.dumps({"failures":failures},ensure_ascii=False))
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
