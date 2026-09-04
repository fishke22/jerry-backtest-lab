from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

TAIPEI = timezone(timedelta(hours=8))
SYMBOL_RE = re.compile(r"^NK225MC[A-Z][0-9]{4}$")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(str(value))
    if dt.tzinfo is None:
        raise RuntimeError("timestamp must be offset-aware")
    return dt


def require_true(obj: dict, key: str) -> None:
    if obj.get(key) is not True:
        raise RuntimeError(f"{key} must be true")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence-manifest", type=Path, required=True)
    ap.add_argument("--image", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--max-age-seconds", type=int, default=900)
    args = ap.parse_args()

    if not args.image.is_file():
        raise RuntimeError("private evidence image does not exist")
    if args.max_age_seconds <= 0:
        raise RuntimeError("max-age-seconds must be positive")

    x = json.loads(args.evidence_manifest.read_text(encoding="utf-8"))
    required = [
        "source_application",
        "source_id",
        "symbol",
        "product",
        "price",
        "currency",
        "source_timestamp",
        "evidence_sha256",
        "exact_product",
        "continuous_contract",
        "source_application_visible",
        "product_name_visible",
        "contract_symbol_visible",
        "price_visible",
        "timestamp_visible",
        "privacy_review_passed",
    ]
    missing = [k for k in required if k not in x]
    if missing:
        raise RuntimeError(f"manifest missing required fields: {missing}")

    if x["source_id"] != "OSE":
        raise RuntimeError("source_id must be OSE")
    symbol = str(x["symbol"])
    if not SYMBOL_RE.fullmatch(symbol):
        raise RuntimeError("symbol must identify an individual OSE Nikkei 225 Micro month contract")
    require_true(x, "exact_product")
    if x.get("continuous_contract") is not False:
        raise RuntimeError("continuous contract is prohibited")

    product = str(x["product"]).lower()
    if "nikkei" not in product or "micro" not in product:
        raise RuntimeError("product must visibly identify Nikkei 225 Micro futures")
    if str(x["currency"]).upper() != "JPY":
        raise RuntimeError("currency must be JPY")
    price = float(x["price"])
    if price <= 0:
        raise RuntimeError("price must be positive")

    for key in [
        "source_application_visible",
        "product_name_visible",
        "contract_symbol_visible",
        "price_visible",
        "timestamp_visible",
        "privacy_review_passed",
    ]:
        require_true(x, key)

    expected_hash = str(x["evidence_sha256"]).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise RuntimeError("evidence_sha256 must be a lowercase/uppercase 64-hex SHA256")
    actual_hash = sha256_file(args.image)
    if actual_hash != expected_hash:
        raise RuntimeError("private evidence image SHA256 mismatch")

    source_ts = parse_dt(str(x["source_timestamp"]))
    now = datetime.now(TAIPEI)
    source_taipei = source_ts.astimezone(TAIPEI)
    age = (now - source_taipei).total_seconds()
    if age < 0:
        raise RuntimeError("source timestamp is in the future")
    if age > args.max_age_seconds:
        raise RuntimeError(
            f"private visual quote stale: age={age:.1f}s > {args.max_age_seconds}s"
        )

    metadata = {
        "version": "1.0",
        "provider": "Private user-provided visual exact-Micro evidence",
        "data_provider_id": "private_visual_evidence",
        "source_application": str(x["source_application"]),
        "source_id": "OSE",
        "symbol": symbol,
        "product": str(x["product"]),
        "price": price,
        "currency": "JPY",
        "source_timestamp": source_taipei.isoformat(),
        "freshness_checked_at": now.isoformat(),
        "freshness_age_seconds": age,
        "maximum_allowed_age_seconds": args.max_age_seconds,
        "freshness_pass": True,
        "exact_product": True,
        "continuous_contract": False,
        "evidence_sha256": actual_hash,
        "raw_evidence_public_git_upload_prohibited": True,
        "privacy_review_passed": True,
        "visual_verification": {
            "source_application_visible": True,
            "product_name_visible": True,
            "contract_symbol_visible": True,
            "price_visible": True,
            "timestamp_visible": True,
        },
        "source_quality_ceiling": "B",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
