from __future__ import annotations

from pathlib import Path

import pandas as pd

import process_jnu_news_language_source_g1 as g1
from process_phase4b_evidence import CACHE, _gdelt_timeline_adaptive


def _direct_windows(start: str, end: str, max_days: int = 31) -> list[tuple[str, str, pd.Timestamp]]:
    s = pd.to_datetime(start, format="%Y%m%d%H%M%S")
    e = pd.to_datetime(end, format="%Y%m%d%H%M%S")
    if not (pd.notna(s) and pd.notna(e) and s < e):
        raise ValueError(f"invalid interval {start}->{end}")
    out = []
    cursor = s
    first = True
    while cursor < e:
        stop = min(cursor + pd.Timedelta(days=max_days), e)
        begin = cursor if first else cursor - pd.Timedelta(seconds=1)
        out.append((begin.strftime("%Y%m%d%H%M%S"), stop.strftime("%Y%m%d%H%M%S"), cursor.normalize()))
        cursor = stop
        first = False
    return out


def gdelt_final_timeline(query: str, mode: str, start: str, end: str, key: str, force: bool) -> pd.Series:
    parts = []
    for i, (a, b) in enumerate(g1.quarter_windows(start, end), start=1):
        quarter_cache = f"g1_{key}_{mode.lower()}_q{i}_{a[:8]}_{b[:8]}.json"
        quarter_path = CACHE / quarter_cache
        if quarter_path.exists() and not force:
            part = _gdelt_timeline_adaptive(query, mode, a, b, quarter_cache, force)
            if i > 1:
                logical_start_day = (pd.to_datetime(a, format="%Y%m%d%H%M%S") + pd.Timedelta(seconds=1)).normalize()
                part = part.loc[part.index >= logical_start_day]
            parts.append(part)
            print(f"g1 final cached quarter: {key} {mode} {a[:8]}->{b[:8]}", flush=True)
            continue

        subparts = []
        for j, (sa, sb, logical_start_day) in enumerate(_direct_windows(a, b), start=1):
            cache = f"g1_{key}_{mode.lower()}_q{i}_{a[:8]}_{b[:8]}_D{j}_{sa[:8]}_{sb[:8]}.json"
            sub = _gdelt_timeline_adaptive(query, mode, sa, sb, cache, force)
            if j > 1:
                sub = sub.loc[sub.index >= logical_start_day]
            subparts.append(sub)
            print(f"g1 final direct chunk: {key} {mode} {sa[:8]}->{sb[:8]}", flush=True)
        if not subparts:
            raise RuntimeError(f"no GDELT data for {key} {mode} quarter {i}")
        part = pd.concat(subparts).groupby(level=0).mean().sort_index()
        if i > 1:
            logical_start_day = (pd.to_datetime(a, format="%Y%m%d%H%M%S") + pd.Timedelta(seconds=1)).normalize()
            part = part.loc[part.index >= logical_start_day]
        parts.append(part)

    if not parts:
        raise RuntimeError(f"no GDELT data for {key} {mode}")
    out = pd.concat(parts).groupby(level=0).mean().sort_index()
    out.name = mode
    return out


def main() -> int:
    g1.gdelt_quarter_timeline = gdelt_final_timeline
    return g1.main()


if __name__ == "__main__":
    raise SystemExit(main())
