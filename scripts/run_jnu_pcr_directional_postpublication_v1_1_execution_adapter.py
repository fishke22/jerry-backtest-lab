from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_RUNNER = ROOT / "scripts" / "run_jnu_pcr_directional_postpublication_v1_1.py"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--prereg", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    prereg_path = Path(args.prereg)
    pre = json.loads(prereg_path.read_text(encoding="utf-8"))
    rules = pre["unchanged_rules"]
    if float(rules["threshold_lower"]) != 88.7 or float(rules["threshold_upper"]) != 116.5:
        raise RuntimeError("frozen thresholds changed")
    if "signal" in pre:
        raise RuntimeError("unexpected signal field; adapter scope changed")
    pre["signal"] = {
        "threshold_lower": rules["threshold_lower"],
        "threshold_upper": rules["threshold_upper"],
    }

    source = SOURCE_RUNNER.read_text(encoding="utf-8-sig")
    bad = '"validated_jnu_module": false,'
    if source.count(bad) != 1:
        raise RuntimeError("unexpected runner boolean-fix scope")
    source = source.replace(bad, '"validated_jnu_module": False,', 1)

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        adapted_pre = td_path / "prereg_v1_1_schema_adapted.json"
        adapted_runner = td_path / "runner_v1_1_boolean_fixed.py"
        adapted_pre.write_text(json.dumps(pre, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        adapted_runner.write_text(source, encoding="utf-8")
        cmd = [
            sys.executable, str(adapted_runner),
            "--panel", args.panel,
            "--prereg", str(adapted_pre),
            "--output", args.output,
            "--report", args.report,
        ]
        raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
