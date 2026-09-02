from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import random
import statistics
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREREG = ROOT / "config" / "jnu_pcr_directional_postpublication_prereg_v1_1.json"
FRED_NIKKEI225_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=NIKKEI225&cosd=2009-07-01&coed=2026-08-31"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def month_add(ym: str, n: int = 1) -> str:
    y, m = map(int, ym.split("-"))
    k = y * 12 + (m - 1) + n
    return f"{k // 12:04d}-{k % 12 + 1:02d}"


def fetch_futures_index() -> tuple[dict[str, list[tuple[date, float]]], str]:
    req = urllib.request.Request(FRED_NIKKEI225_CSV, headers={"User-Agent": "JerryBacktestLab/PCR-Replication-1.1"})
    with urllib.request.urlopen(req, timeout=60) as response:
        raw = response.read()
    text = raw.decode("utf-8-sig", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or rows[0][:2] != ["observation_date", "NIKKEI225"]:
        raise RuntimeError("Unexpected FRED NIKKEI225 CSV shape")
    out: dict[str, list[tuple[date, float]]] = {}
    for row in rows[1:]:
        if len(row) < 2 or row[1].strip() in {"", "."}:
            continue
        try:
            d = date.fromisoformat(row[0].strip())
            v = float(row[1].strip())
        except Exception:
            continue
        out.setdefault(f"{d.year:04d}-{d.month:02d}", []).append((d, v))
    for ym in out:
        out[ym].sort(key=lambda x: x[0])
    if "2009-08" not in out or "2026-08" not in out:
        raise RuntimeError("FRED NIKKEI225 does not cover preregistered sample")
    return out, sha256_bytes(raw)


def cumulative(returns: list[float]) -> float:
    wealth = 1.0
    for r in returns:
        wealth *= 1.0 + r
    return wealth - 1.0


def sharpe_monthly(returns: list[float]) -> float | None:
    if len(returns) < 2:
        return None
    sd = statistics.stdev(returns)
    if sd == 0:
        return None
    return statistics.mean(returns) / sd * math.sqrt(12.0)


def bootstrap_lower(returns: list[float], block: int, resamples: int, seed: int) -> float:
    if len(returns) < block:
        raise RuntimeError("Not enough months for requested bootstrap block length")
    rng = random.Random(seed)
    n = len(returns)
    starts = list(range(0, n - block + 1))
    means: list[float] = []
    for _ in range(resamples):
        sample: list[float] = []
        while len(sample) < n:
            s = rng.choice(starts)
            sample.extend(returns[s:s + block])
        sample = sample[:n]
        means.append(sum(sample) / n)
    means.sort()
    idx = max(0, min(len(means) - 1, int(math.floor(0.025 * len(means)))))
    return means[idx]


def period_cumulative(records: list[dict], start: str, end: str, key: str) -> float:
    rs = [float(r[key]) for r in records if start <= r["return_month"] <= end]
    return cumulative(rs) if rs else float("nan")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True, type=Path)
    ap.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    ap.add_argument("--output", type=Path, default=ROOT / "results" / "jnu_pcr_directional_postpublication_v1_1.json")
    ap.add_argument("--report", type=Path, default=ROOT / "reports" / "jnu_pcr_directional_postpublication_v1_1.md")
    args = ap.parse_args()

    pre = load_json(args.prereg)
    panel = load_json(args.panel)
    if pre["directional_outcome_inspected_before_freeze"] is not False:
        raise RuntimeError("preregistration is not pre-outcome")
    if panel.get("data_feasibility_pass") is not True:
        raise RuntimeError("authoritative PCR panel did not pass Data Gate")
    if panel.get("directional_return_outcomes_used") is not False:
        raise RuntimeError("PCR panel already contains directional outcomes")

    market, market_sha = fetch_futures_index()
    month_map = {m["month"]: m for m in panel["months"]}
    start = pre["evaluation_sample"]["signal_month_start"]
    end = pre["evaluation_sample"]["signal_month_end"]
    lo = float(pre["signal"]["threshold_lower"])
    hi = float(pre["signal"]["threshold_upper"])
    primary_cost = float(pre["costs"]["primary_one_way_bps"]) / 10000.0
    stress_cost = float(pre["costs"]["stress_one_way_bps"]) / 10000.0

    records: list[dict] = []
    prev_pos = 0
    ym = start
    while ym <= end:
        m = month_map.get(ym)
        if m is None:
            raise RuntimeError(f"missing preregistered signal month {ym}")
        pcr = m.get("monthly_pcr") if m.get("status") == "PCR_DEFINED" else None
        if pcr is None:
            pos = 0
        elif float(pcr) > hi:
            pos = 1
        elif float(pcr) < lo:
            pos = -1
        else:
            pos = 0
        ret_month = month_add(ym, 1)
        levels = market.get(ret_month)
        if not levels:
            raise RuntimeError(f"missing official Futures Index return month {ret_month}")
        first_d, first_v = levels[0]
        last_d, last_v = levels[-1]
        gross_market = last_v / first_v - 1.0
        turnover = abs(pos - prev_pos)
        primary_net = pos * gross_market - turnover * primary_cost
        stress_net = pos * gross_market - turnover * stress_cost

        secondary = None
        signal_levels = market.get(ym)
        if signal_levels:
            secondary = pos * (last_v / signal_levels[-1][1] - 1.0) - turnover * primary_cost

        records.append({
            "signal_month": ym,
            "return_month": ret_month,
            "pcr_status": m.get("status"),
            "monthly_pcr": pcr,
            "position": pos,
            "turnover_units": turnover,
            "return_first_date": first_d.isoformat(),
            "return_last_date": last_d.isoformat(),
            "market_first_level": first_v,
            "market_last_level": last_v,
            "market_first_to_last_return": gross_market,
            "primary_net_return": primary_net,
            "stress_20bps_net_return": stress_net,
            "secondary_diagnostic_net_return": secondary,
        })
        prev_pos = pos
        ym = month_add(ym, 1)

    primary_returns = [float(r["primary_net_return"]) for r in records]
    stress_returns = [float(r["stress_20bps_net_return"]) for r in records]
    active = [r for r in records if r["position"] != 0]
    boot = pre["statistics"]["bootstrap"]
    lower95 = bootstrap_lower(primary_returns, int(boot["block_length_months"]), int(boot["resamples"]), int(boot["seed"]))

    subdefs = [
        ("2009-08_2013-12", "2009-08", "2013-12"),
        ("2014-01_2018-12", "2014-01", "2018-12"),
        ("2019-01_2022-12", "2019-01", "2022-12"),
        ("2023-01_2026-08", "2023-01", "2026-08"),
    ]
    subperiods = {name: period_cumulative(records, a, b, "primary_net_return") for name, a, b in subdefs}
    positive_subperiods = sum(1 for v in subperiods.values() if v > 0)
    recent_cum = subperiods["2023-01_2026-08"]
    primary_cum = cumulative(primary_returns)
    stress_cum = cumulative(stress_returns)
    primary_sharpe = sharpe_monthly(primary_returns)

    gate_cfg = pre["mechanical_pass_gate"]
    checks = {
        "minimum_active_months": len(active) >= int(gate_cfg["minimum_active_months"]),
        "primary_net_cumulative_return": primary_cum > float(gate_cfg["primary_net_cumulative_return_gt"]),
        "primary_net_annualized_sharpe": primary_sharpe is not None and primary_sharpe > float(gate_cfg["primary_net_annualized_sharpe_gt"]),
        "bootstrap_lower_mean_monthly_net_return": lower95 > float(gate_cfg["bootstrap_95pct_lower_bound_mean_monthly_net_return_gt"]),
        "stress_20bps_net_cumulative_return": stress_cum > float(gate_cfg["stress_20bps_net_cumulative_return_gt"]),
        "positive_fixed_subperiods": positive_subperiods >= int(gate_cfg["minimum_positive_fixed_subperiods"]),
        "recent_window_net_cumulative_return": recent_cum > float(gate_cfg["recent_window_net_cumulative_return_gt"]),
    }
    passed = all(checks.values())
    status = pre["classification"]["pass"] if passed else pre["classification"]["fail"]

    result = {
        "version": "1.0",
        "candidate_id": pre["candidate_id"],
        "status": status,
        "mechanical_pass": passed,
        "validated_jnu_module": false,
        "preregistration": str(args.prereg.relative_to(ROOT)).replace("\\", "/") if args.prereg.is_relative_to(ROOT) else str(args.prereg),
        "source": {
            "pcr_panel_sha256": sha256_file(args.panel),
            "prereg_sha256": sha256_file(args.prereg),
            "nikkei_futures_index_url": FRED_NIKKEI225_CSV,
            "nikkei_futures_index_sha256": market_sha,
        },
        "sample": {
            "signal_month_start": start,
            "signal_month_end": end,
            "return_month_start": records[0]["return_month"],
            "return_month_end": records[-1]["return_month"],
            "calendar_months": len(records),
            "active_months": len(active),
        },
        "metrics": {
            "primary_net_cumulative_return": primary_cum,
            "primary_mean_monthly_net_return": statistics.mean(primary_returns),
            "primary_annualized_sharpe": primary_sharpe,
            "stress_20bps_net_cumulative_return": stress_cum,
            "bootstrap_95pct_lower_bound_mean_monthly_net_return": lower95,
            "positive_fixed_subperiods": positive_subperiods,
            "recent_window_net_cumulative_return": recent_cum,
            "subperiod_net_cumulative_returns": subperiods,
        },
        "checks": checks,
        "records": records,
        "interpretation": "A PASS is a post-publication daily Futures Index proxy replication only and is not exact-JNU validation.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# JNU PCR post-publication directional replication v1.1",
        "",
        f"- Status: **{status}**",
        f"- Mechanical PASS: **{passed}**",
        "- Validated exact-JNU module: **false**",
        f"- Active months: **{len(active)} / {len(records)}**",
        f"- Primary net cumulative return: **{primary_cum:.6f}**",
        f"- Primary annualized Sharpe: **{primary_sharpe}**",
        f"- 20 bps stress cumulative return: **{stress_cum:.6f}**",
        f"- Bootstrap 95% lower mean monthly return: **{lower95:.8f}**",
        f"- Positive fixed subperiods: **{positive_subperiods} / 4**",
        f"- Recent 2023-01..2026-08 cumulative return: **{recent_cum:.6f}**",
        "",
        "## Gate checks",
    ]
    lines.extend([f"- {k}: **{v}**" for k, v in checks.items()])
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "metrics": result["metrics"], "checks": checks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


