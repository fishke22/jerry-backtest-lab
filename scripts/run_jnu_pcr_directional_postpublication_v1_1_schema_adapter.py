from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_jnu_pcr_directional_postpublication_v1_1.py"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--prereg", required=True)
    ap.add_argument("--output", default=str(ROOT / "results" / "jnu_pcr_directional_postpublication_v1_1.json"))
    ap.add_argument("--report", default=str(ROOT / "reports" / "jnu_pcr_directional_postpublication_v1_1.md"))
    args = ap.parse_args()

    prereg_path = Path(args.prereg)
    pre = json.loads(prereg_path.read_text(encoding="utf-8"))
    rules = pre["unchanged_rules"]
    if float(rules["threshold_lower"]) != 88.7 or float(rules["threshold_upper"]) != 116.5:
        raise RuntimeError("frozen v1.1 thresholds changed")
    if "signal" in pre:
        raise RuntimeError("unexpected signal field already present; adapter scope changed")
    pre["signal"] = {
        "threshold_lower": rules["threshold_lower"],
        "threshold_upper": rules["threshold_upper"],
    }

    with tempfile.TemporaryDirectory() as td:
        adapted = Path(td) / "prereg_v1_1_schema_adapted.json"
        adapted.write_text(json.dumps(pre, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        cmd = [
            sys.executable,
            str(RUNNER),
            "--panel", args.panel,
            "--prereg", str(adapted),
            "--output", args.output,
            "--report", args.report,
        ]
        raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
