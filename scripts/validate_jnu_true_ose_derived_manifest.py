#!/usr/bin/env python3
"""Fail-closed validator for non-reconstructive true-OSE derived manifests.

This script intentionally does NOT parse or upload personally licensed raw data.
It validates the provenance/data-quality manifest produced locally after an
authorized raw-schema audit and normalization step.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL = {
    "source_hashes",
    "source_license_classification",
    "parser_version_commit",
    "calendar_session_version",
    "product_contract_coverage",
    "date_range",
    "missingness_summary",
    "duplicate_summary",
    "derived_feature_definitions",
    "derived_output_hash",
    "raw_data_cloud_uploaded",
    "critical_data_quality_issues",
}


def fail(message: str) -> None:
    raise SystemExit(f"JNU_TRUE_OSE_MANIFEST_FAIL: {message}")


def require_nonempty(value: Any, name: str) -> None:
    if value is None or value == "" or value == [] or value == {}:
        fail(f"{name} must be non-empty")


def validate_sha256(value: str, name: str) -> None:
    if len(value) != 64:
        fail(f"{name} must be a 64-char sha256 hex digest")
    try:
        int(value, 16)
    except ValueError:
        fail(f"{name} is not hexadecimal")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--derived-file",
        type=Path,
        default=None,
        help="Optional local derived file whose SHA-256 must match derived_output_hash.",
    )
    args = parser.parse_args()

    if not args.manifest.is_file():
        fail(f"manifest not found: {args.manifest}")

    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except Exception as exc:  # fail closed on malformed JSON
        fail(f"cannot parse manifest JSON: {exc}")

    missing = sorted(REQUIRED_TOP_LEVEL - set(data))
    if missing:
        fail(f"missing required fields: {', '.join(missing)}")

    if data["raw_data_cloud_uploaded"] is not False:
        fail("raw_data_cloud_uploaded must be false")

    issues = data["critical_data_quality_issues"]
    if not isinstance(issues, list):
        fail("critical_data_quality_issues must be a list")
    if issues:
        fail("critical data-quality issues remain unresolved")

    source_hashes = data["source_hashes"]
    if not isinstance(source_hashes, list) or not source_hashes:
        fail("source_hashes must be a non-empty list")
    for index, item in enumerate(source_hashes):
        if not isinstance(item, dict):
            fail(f"source_hashes[{index}] must be an object")
        require_nonempty(item.get("source_id"), f"source_hashes[{index}].source_id")
        digest = item.get("sha256")
        if not isinstance(digest, str):
            fail(f"source_hashes[{index}].sha256 must be a string")
        validate_sha256(digest, f"source_hashes[{index}].sha256")

    for field in (
        "source_license_classification",
        "parser_version_commit",
        "calendar_session_version",
        "product_contract_coverage",
        "date_range",
        "missingness_summary",
        "duplicate_summary",
        "derived_feature_definitions",
    ):
        require_nonempty(data[field], field)

    derived_hash = data["derived_output_hash"]
    if not isinstance(derived_hash, str):
        fail("derived_output_hash must be a string")
    validate_sha256(derived_hash, "derived_output_hash")

    if args.derived_file is not None:
        if not args.derived_file.is_file():
            fail(f"derived file not found: {args.derived_file}")
        actual = sha256_file(args.derived_file)
        if actual.lower() != derived_hash.lower():
            fail("derived_output_hash does not match --derived-file")

    print("JNU_TRUE_OSE_DERIVED_MANIFEST_PASS")


if __name__ == "__main__":
    main()
