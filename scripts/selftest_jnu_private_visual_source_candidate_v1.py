from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_jnu_private_visual_exact_micro_source_metadata_v1.py"
TAIPEI = timezone(timedelta(hours=8))


def run(manifest: Path, image: Path, output: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--evidence-manifest",
            str(manifest),
            "--image",
            str(image),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def write_manifest(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="jnu_private_visual_selftest_") as td:
        t = Path(td)
        image = t / "private_quote_evidence.bin"
        image.write_bytes(b"SYNTHETIC_PRIVATE_EVIDENCE_SELFTEST_ONLY\x00\x01")
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        now = datetime.now(TAIPEI)

        base = {
            "source_application": "SELFTEST Exact OSE Micro Display",
            "source_id": "OSE",
            "symbol": "NK225MCU2026",
            "product": "Nikkei 225 micro Futures Sep 2026",
            "price": 65000,
            "currency": "JPY",
            "source_timestamp": (now - timedelta(seconds=30)).isoformat(),
            "evidence_sha256": digest,
            "exact_product": True,
            "continuous_contract": False,
            "source_application_visible": True,
            "product_name_visible": True,
            "contract_symbol_visible": True,
            "price_visible": True,
            "timestamp_visible": True,
            "privacy_review_passed": True,
        }

        cases = []

        def case(name: str, obj: dict, expect_ok: bool, error_substring: str | None = None):
            m = t / f"{name}.json"
            o = t / f"{name}.out.json"
            write_manifest(m, obj)
            cp = run(m, image, o)
            ok = cp.returncode == 0
            passed = ok == expect_ok
            if error_substring and not ok:
                passed = passed and error_substring in (cp.stdout + cp.stderr)
            rec = {
                "name": name,
                "expected_ok": expect_ok,
                "returncode": cp.returncode,
                "pass": passed,
                "error_substring": error_substring,
            }
            if ok:
                rec["metadata"] = json.loads(o.read_text(encoding="utf-8"))
            else:
                rec["stderr_tail"] = (cp.stderr or cp.stdout)[-500:]
            cases.append(rec)

        case("valid", dict(base), True)

        stale = dict(base)
        stale["source_timestamp"] = (now - timedelta(seconds=901)).isoformat()
        case("stale", stale, False, "stale")

        bad_hash = dict(base)
        bad_hash["evidence_sha256"] = "0" * 64
        case("hash_mismatch", bad_hash, False, "SHA256 mismatch")

        cont = dict(base)
        cont["continuous_contract"] = True
        case("continuous", cont, False, "continuous contract is prohibited")

        bad_symbol = dict(base)
        bad_symbol["symbol"] = "NK225MC1!"
        case("invalid_symbol", bad_symbol, False, "individual OSE Nikkei 225 Micro month contract")

        result = {
            "version": "1.0",
            "status": "PASS" if all(x["pass"] for x in cases) else "FAIL",
            "cases": cases,
            "raw_test_image_persisted": False,
            "real_live_shadow_forecast_created": False,
        }
        Path("private_visual_source_selftest.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["status"] != "PASS":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
