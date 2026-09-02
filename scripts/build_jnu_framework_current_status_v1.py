from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "config" / "jnu_family_attempt_ledger.json"
GAP = ROOT / "config" / "jnu_framework_completion_gap_20260902.json"
READINESS = ROOT / "stage8_readiness" / "jnu_stage8_readiness_v1.json"
STAGE9 = ROOT / "stage9_results" / "jnu_stage9_role_validation_v1.json"
MEMORY = ROOT / "config" / "jnu_validated_framework_memory_20260901.json"
OUTPUT = ROOT / "framework_status" / "jnu_framework_current_status_v1.json"
REPORT = ROOT / "framework_status" / "jnu_framework_current_status_v1.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ledger = load(LEDGER)
    gap = load(GAP)
    ready = load(READINESS)
    stage9 = load(STAGE9)
    memory = load(MEMORY)

    total = int(gap["major_candidates_total"])
    terminal = int(gap["major_candidates_terminal"])
    pending = int(gap["major_candidates_pending"])
    if total != terminal + pending:
        raise RuntimeError("completion count mismatch")

    har = ready["HAR_RSV"]
    boj = ready["BOJ_MPM"]
    if ready.get("performance_metrics_computed") is not False:
        raise RuntimeError("fail closed: readiness artifact must not contain computed performance")
    if har.get("performance_columns_read") is not False:
        raise RuntimeError("fail closed: HAR readiness must not read performance columns")
    if boj.get("event_effect_columns_read") is not False:
        raise RuntimeError("fail closed: BOJ readiness must not read effect columns")

    s9mods = stage9["modules"]
    validated = int(stage9["validated_jnu_modules_from_this_review"])
    directional = int(stage9["validated_directional_modules_from_this_review"])
    decision = stage9["decision_engine_direction"]

    if directional != 0 or decision != "NO_VALIDATED_DIRECTIONAL_EDGE":
        raise RuntimeError("unexpected directional promotion in current framework status")

    if pending:
        framework_status = "FRAMEWORK_INCOMPLETE_PENDING_STAGE8_FORWARD_DATA"
    elif directional > 0:
        framework_status = "FRAMEWORK_COMPLETE_WITH_VALIDATED_EDGE"
    else:
        framework_status = "FRAMEWORK_COMPLETE_NO_VALIDATED_DIRECTIONAL_EDGE"

    terminal_map = gap["terminal"]
    pending_map = gap["pending_finalists"]

    result = {
        "version": "1.0",
        "as_of_utc": datetime.now(timezone.utc).isoformat(),
        "framework_status": framework_status,
        "major_candidates": {
            "total": total,
            "terminal": terminal,
            "pending": pending,
            "terminal_classifications": terminal_map,
        },
        "validated_modules": {
            "jnu_modules": validated,
            "directional_modules": directional,
            "decision_engine_direction": decision,
        },
        "pending_finalists": {
            "HAR_RSV": {
                "role": pending_map["HAR_RSV_TRUE_OSE_CONFIRMATION"]["role"],
                "stage3_status": pending_map["HAR_RSV_TRUE_OSE_CONFIRMATION"]["current_status"],
                "stage8_readiness": har["status"],
                "available_new_days": har["available_new_days"],
                "required_new_days": har["required_new_days"],
                "remaining_new_days": har["remaining_new_days"],
                "stage9_status": s9mods["HAR_RSV_DI1"]["status"],
            },
            "BOJ_MPM": {
                "role": pending_map["BOJ_MPM_EVENT_VOLATILITY"]["role"],
                "stage3_status": pending_map["BOJ_MPM_EVENT_VOLATILITY"]["current_status"],
                "stage8_readiness": boj["status"],
                "available_new_events": boj["available_new_events"],
                "required_new_events": boj["required_new_events"],
                "remaining_new_events": boj["remaining_new_events"],
                "stage9_status": s9mods["BOJ_MPM_EVENT_VOLATILITY_G1"]["status"],
            },
        },
        "next_legal_actions": [
            "Accumulate untouched exact-JNU observations after the preregistered Stage8 cutoffs.",
            "Run scripts/check_jnu_stage8_readiness_v1.py or the cloud readiness workflow after derived panels/manifests update.",
            "Run a Stage8 outcome runner only when its readiness status is READY_TO_RUN_STAGE8.",
            "If Stage8 passes, run the preregistered fail-closed Stage9 role review without changing the module role.",
            "When both pending finalists are terminally classified, run the final framework completion audit.",
        ],
        "hard_blocks": [
            "No partial Stage8 performance inspection.",
            "No historical sample carve-out to manufacture a holdout.",
            "No rejected-family parameter rescue.",
            "No risk/event module may become a directional vote without a separate validated directional family.",
        ],
        "artifact_hashes": {
            "family_attempt_ledger": sha256_file(LEDGER),
            "completion_gap": sha256_file(GAP),
            "stage8_readiness": sha256_file(READINESS),
            "stage9_review": sha256_file(STAGE9),
            "validated_framework_memory": sha256_file(MEMORY),
        },
        "source_state": {
            "ledger_version": ledger.get("version"),
            "completion_gap_status": gap.get("status"),
            "stage8_readiness_status": ready.get("status"),
            "stage9_status": stage9.get("status"),
            "memory_framework_status": memory.get("framework_status"),
        },
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# JNU Framework Current Status v1",
        "",
        f"- Framework: **{framework_status}**",
        f"- Major candidates terminal: **{terminal} / {total}**",
        f"- Pending finalists: **{pending}**",
        f"- Validated JNU modules: **{validated}**",
        f"- Validated directional modules: **{directional}**",
        f"- Direction engine: **{decision}**",
        "",
        "## Pending finalists",
        f"- HAR-RSV: Stage3 PASS; Stage8 **{har['available_new_days']}/{har['required_new_days']}** new JNU days; Stage9 {s9mods['HAR_RSV_DI1']['status']}.",
        f"- BOJ MPM: Stage3 PASS; Stage8 **{boj['available_new_events']}/{boj['required_new_events']}** new eligible events; Stage9 {s9mods['BOJ_MPM_EVENT_VOLATILITY_G1']['status']}.",
        "",
        "## Current rule",
        "- No validated directional edge exists. Risk/event candidates remain role-constrained and cannot be converted into directional votes.",
        "- Stage8 outcome inspection stays locked until the readiness gate is satisfied.",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
