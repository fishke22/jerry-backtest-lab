from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

TAIPEI = timezone(timedelta(hours=8))
REQUEST_ID_RE = re.compile(r"^JNU_REQ_[A-Za-z0-9._-]{8,120}$")
MICRO_RE = re.compile(r"^NK225MC[A-Z][0-9]{4}$")

FORBIDDEN_REQUEST_FIELDS = {
    "reference_price",
    "reference_timestamp",
    "reference_source",
    "reference_source_metadata",
    "bias",
    "confidence",
    "decision_trace",
}

REQUIRED_REQUEST_FIELDS = [
    "request_id",
    "request_created_at_taipei",
    "request_valid_until_taipei",
    "symbol",
    "target_day_session_date",
    "decision_input",
    "expected_path",
    "key_levels",
    "invalidation_conditions",
    "event_risk",
    "flip_conditions",
    "evidence_summary",
]


def load(path: Path) -> dict:
    x = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(x, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return x


def validate_request(x: dict) -> None:
    missing = [k for k in REQUIRED_REQUEST_FIELDS if k not in x]
    if missing:
        raise RuntimeError(f"missing request fields: {missing}")
    forbidden = sorted(k for k in FORBIDDEN_REQUEST_FIELDS if k in x)
    if forbidden:
        raise RuntimeError(
            "request must not carry quote/outcome-derived fields; cloud runner owns them: "
            + ", ".join(forbidden)
        )
    rid = str(x["request_id"])
    if not REQUEST_ID_RE.fullmatch(rid):
        raise RuntimeError("invalid request_id; expected JNU_REQ_<unique token>")
    symbol = str(x["symbol"]).upper()
    if not MICRO_RE.fullmatch(symbol):
        raise RuntimeError("symbol must be an individual OSE Nikkei 225 Micro month contract")
    if not isinstance(x["decision_input"], dict):
        raise RuntimeError("decision_input must be an object")
    datetime.fromisoformat(str(x["target_day_session_date"]))
    req_created = datetime.fromisoformat(str(x["request_created_at_taipei"]))
    req_until = datetime.fromisoformat(str(x["request_valid_until_taipei"]))
    if req_created.tzinfo is None or req_until.tzinfo is None:
        raise RuntimeError("request timestamps must be offset-aware")
    req_created = req_created.astimezone(TAIPEI)
    req_until = req_until.astimezone(TAIPEI)
    lifetime = (req_until - req_created).total_seconds()
    if lifetime <= 0 or lifetime > 900:
        raise RuntimeError("request validity window must be >0 and <=900 seconds")
    if not isinstance(x["key_levels"], list) or not x["key_levels"]:
        raise RuntimeError("key_levels must be a non-empty array")
    for k in [
        "expected_path",
        "invalidation_conditions",
        "event_risk",
        "flip_conditions",
        "evidence_summary",
    ]:
        if not str(x[k]).strip():
            raise RuntimeError(f"{k} must be non-empty")


def validate_quote(q: dict, request: dict) -> None:
    symbol = str(request["symbol"]).upper()
    if q.get("symbol") != symbol:
        raise RuntimeError("quote symbol does not match request symbol")
    if q.get("tradingview_symbol") != f"OSE:{symbol}":
        raise RuntimeError("quote TradingView symbol identity mismatch")
    if q.get("source_id") != "OSE":
        raise RuntimeError("quote source_id must be OSE")
    if q.get("exact_product") is not True:
        raise RuntimeError("quote exact_product must be true")
    if q.get("continuous_contract") is not False:
        raise RuntimeError("continuous contract cannot be a scored primary reference")
    if q.get("freshness_pass") is not True:
        raise RuntimeError("quote freshness_pass must be true")
    age = float(q.get("freshness_age_seconds"))
    if age < 0 or age > 900:
        raise RuntimeError("quote age exceeds 900 seconds")
    if float(q.get("price")) <= 0:
        raise RuntimeError("quote price must be positive")
    ts = datetime.fromisoformat(str(q.get("source_timestamp")))
    if ts.tzinfo is None:
        raise RuntimeError("quote source timestamp must be offset-aware")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", type=Path, required=True)
    ap.add_argument("--quote", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--created-at-taipei", default=None)
    args = ap.parse_args()

    req = load(args.request)
    q = load(args.quote)
    validate_request(req)
    validate_quote(q, req)

    created = (
        datetime.fromisoformat(args.created_at_taipei)
        if args.created_at_taipei
        else datetime.now(TAIPEI)
    )
    if created.tzinfo is None:
        raise RuntimeError("created_at_taipei must be offset-aware")
    created = created.astimezone(TAIPEI)
    req_created = datetime.fromisoformat(str(req["request_created_at_taipei"])).astimezone(TAIPEI)
    req_until = datetime.fromisoformat(str(req["request_valid_until_taipei"])).astimezone(TAIPEI)
    if created < req_created:
        raise RuntimeError("forecast-build time precedes request creation")
    if created > req_until:
        raise RuntimeError("cloud forecast request expired before forecast-build time")
    source_ts = datetime.fromisoformat(str(q["source_timestamp"])).astimezone(TAIPEI)
    age = (created - source_ts).total_seconds()
    if age < 0 or age > 900:
        raise RuntimeError(
            f"quote no longer fresh at forecast-build time: age={age:.1f}s"
        )

    meta = dict(q)
    meta["freshness_checked_at_forecast_build"] = created.isoformat()
    meta["freshness_age_seconds"] = age
    meta["freshness_pass"] = True

    envelope = {
        "request_id": req["request_id"],
        "request_created_at_taipei": req_created.isoformat(),
        "request_valid_until_taipei": req_until.isoformat(),
        "created_at_taipei": created.isoformat(),
        "reference_price": float(q["price"]),
        "reference_timestamp": source_ts.isoformat(),
        "reference_source": "TradingView public OSE individual Micro quote-session",
        "reference_source_metadata": meta,
        "exact_product": True,
        "target_day_session_date": req["target_day_session_date"],
        "decision_input": req["decision_input"],
        "expected_path": req["expected_path"],
        "key_levels": req["key_levels"],
        "invalidation_conditions": req["invalidation_conditions"],
        "event_risk": req["event_risk"],
        "flip_conditions": req["flip_conditions"],
        "evidence_summary": req["evidence_summary"],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "CLOUD_FORECAST_INPUT_BUILT",
                "request_id": req["request_id"],
                "symbol": req["symbol"],
                "reference_price": envelope["reference_price"],
                "reference_timestamp": envelope["reference_timestamp"],
                "freshness_age_seconds": age,
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
