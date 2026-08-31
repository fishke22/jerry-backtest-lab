from __future__ import annotations

import hashlib
import json
import math
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dpd_results" / "jnu_cme_nkd_jpn225_alignment_g0.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "cme_nkd": "https://raw.githubusercontent.com/axb0306/cme-futures-ohlc/main/NKD/NKD_1min_20260308_20260415.csv",
    "jpn225": "https://raw.githubusercontent.com/getdata-finance/jpn225-1m-ohlcv-index-historical-data/main/JPN225_1m.csv",
}
LAGS = list(range(-6, 7))
MIN_COMMON = 1000
ROLL = 288


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "JerryBacktestLab/DPD-Alignment-G0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse(raw: bytes) -> pd.DataFrame:
    import io
    d = pd.read_csv(io.BytesIO(raw))
    cols = {c.lower(): c for c in d.columns}
    dt = cols.get("datetime") or cols.get("timestamp") or cols.get("date")
    close = cols.get("close")
    if not dt or not close:
        raise RuntimeError(f"required columns missing: {list(d.columns)}")
    idx = pd.to_datetime(d[dt], utc=True, errors="coerce")
    close_values = pd.to_numeric(d[close], errors="coerce").to_numpy()
    # Important: construct positionally. Passing the original Series alongside a
    # DatetimeIndex makes pandas align RangeIndex labels to timestamps, producing
    # all-NaN close values and a false zero-overlap failure.
    x = pd.DataFrame({"close": close_values}, index=pd.DatetimeIndex(idx))
    x = x[~x.index.isna()].dropna().sort_index()
    x = x[~x.index.duplicated(keep="last")]
    return x


def ret5(x: pd.DataFrame) -> pd.Series:
    px = x["close"].resample("5min").last().dropna()
    return np.log(px).diff().dropna()


def safe_corr(a: pd.Series, b: pd.Series) -> float | None:
    z = pd.concat([a, b], axis=1).dropna()
    if len(z) < 3:
        return None
    v = float(z.iloc[:, 0].corr(z.iloc[:, 1]))
    return None if not math.isfinite(v) else v


def main() -> None:
    raws = {k: fetch(v) for k, v in SOURCES.items()}
    dfs = {k: parse(v) for k, v in raws.items()}
    r = {k: ret5(v) for k, v in dfs.items()}
    common = r["cme_nkd"].index.intersection(r["jpn225"].index)
    if len(common) < MIN_COMMON:
        raise RuntimeError(
            "insufficient common bars: "
            f"{len(common)} < {MIN_COMMON}; "
            f"cme={dfs['cme_nkd'].index.min()}..{dfs['cme_nkd'].index.max()} "
            f"jpn={dfs['jpn225'].index.min()}..{dfs['jpn225'].index.max()}"
        )

    cme = r["cme_nkd"].reindex(common)
    jpn = r["jpn225"].reindex(common)
    lag_corr = {}
    for lag in LAGS:
        # corr(CME_t, JPN_{t+lag}) implemented by shifting JPN backward by lag.
        lag_corr[str(lag)] = safe_corr(cme, jpn.shift(-lag))

    finite = [(int(k), v) for k, v in lag_corr.items() if v is not None]
    best_lag, best_corr = max(finite, key=lambda kv: abs(kv[1]))

    pair = pd.concat([cme.rename("cme"), jpn.rename("jpn")], axis=1).dropna()
    roll = pair["cme"].rolling(ROLL).corr(pair["jpn"]).dropna()

    result = {
        "candidate_id": "CME_NKD_JPN225_ALIGNMENT_G0",
        "status": "SOURCE_FEASIBILITY_COMPLETE",
        "promotion_power": "NONE",
        "implementation_revision": "DI1_POSITIONAL_VALUE_ALIGNMENT_FIX_ONLY",
        "source": {
            k: {
                "url": SOURCES[k],
                "sha256": sha256(raws[k]),
                "first_timestamp": dfs[k].index.min().isoformat(),
                "last_timestamp": dfs[k].index.max().isoformat(),
                "rows": int(len(dfs[k])),
            }
            for k in SOURCES
        },
        "diagnostics": {
            "cme_duplicates_after_normalization": 0,
            "jpn_duplicates_after_normalization": 0,
            "common_5m_bars": int(len(pair)),
            "common_from": pair.index.min().isoformat(),
            "common_to": pair.index.max().isoformat(),
        },
        "return_association": {
            "contemporaneous_corr": safe_corr(pair["cme"], pair["jpn"]),
            "lag_grid_corr": lag_corr,
            "max_abs_corr_lag_5m_units": int(best_lag),
            "max_abs_corr": float(best_corr),
            "rolling_corr_window_bars": ROLL,
            "rolling_corr_n": int(len(roll)),
            "rolling_corr_median": float(roll.median()) if len(roll) else None,
            "rolling_corr_q25": float(roll.quantile(0.25)) if len(roll) else None,
            "rolling_corr_q75": float(roll.quantile(0.75)) if len(roll) else None,
        },
        "interpretation": "Technical source-alignment feasibility only. CME NKD is a true CME venue series, but JPN225 is not OSE; no OSE leadership or directional-alpha inference is permitted.",
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "common_5m_bars": result["diagnostics"]["common_5m_bars"], "best_lag": best_lag, "best_corr": best_corr}))


if __name__ == "__main__":
    main()
