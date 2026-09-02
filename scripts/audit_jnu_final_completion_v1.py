from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "config" / "jnu_final_completion_audit_prereg_v1.json"
CRITERIA = ROOT / "config" / "jnu_framework_completion_criteria_v1.json"
LEDGER = ROOT / "config" / "jnu_family_attempt_ledger.json"
GAP = ROOT / "config" / "jnu_framework_completion_gap_20260902.json"
CURRENT = ROOT / "framework_status" / "jnu_framework_current_status_v1.json"
STAGE9 = ROOT / "stage9_results" / "jnu_stage9_role_validation_v1.json"
OUTPUT = ROOT / "final_audit" / "jnu_final_completion_audit_v1.json"
REPORT = ROOT / "final_audit" / "jnu_final_completion_audit_v1.md"


def load(path: Path) -> dict:
    if not path.exists():
        raise RuntimeError(f"missing required artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    prereg=load(PREREG)
    criteria=load(CRITERIA)
    ledger=load(LEDGER)
    gap=load(GAP)
    current=load(CURRENT)
    stage9=load(STAGE9)

    expected=set(prereg["major_candidate_set"])
    criteria_set=set(criteria["major_candidate_set"])
    if expected != criteria_set or len(expected) != 8:
        raise RuntimeError("major-candidate set mismatch against frozen completion criteria")

    # Six static terminal dispositions are recorded by the completion-gap audit.
    dispositions=dict(gap["terminal"])

    har9=stage9["modules"]["HAR_RSV_DI1"]["status"]
    boj9=stage9["modules"]["BOJ_MPM_EVENT_VOLATILITY_G1"]["status"]

    def stage9_disposition(status: str) -> str | None:
        if status=="VALIDATED_JNU_MODULE_ROLE_CONSTRAINED":
            return status
        if status=="STAGE9_NOT_ADMITTED":
            return status
        if status=="STAGE9_BLOCKED_STAGE8_PENDING":
            return None
        raise RuntimeError(f"unknown Stage9 status: {status}")

    har_disp=stage9_disposition(har9)
    boj_disp=stage9_disposition(boj9)
    if har_disp is not None:
        dispositions["HAR_RSV_TRUE_OSE_CONFIRMATION"]=har_disp
    if boj_disp is not None:
        dispositions["BOJ_MPM_EVENT_VOLATILITY"]=boj_disp

    missing=sorted(expected-set(dispositions))
    extra=sorted(set(dispositions)-expected)
    if extra:
        raise RuntimeError(f"unexpected major-candidate dispositions: {extra}")

    terminal_classes=set(prereg["terminal_status_classes"])
    nonterminal={k:v for k,v in dispositions.items() if v not in terminal_classes}
    if nonterminal:
        raise RuntimeError(f"unrecognized nonterminal classifications: {nonterminal}")

    # Permanent-attempt-ledger integrity for outcome-tested PCR family and key major tested families.
    ids={row["id"] for row in ledger["families"]}
    ledger_required={
        "NIKKEI225_OPTIONS_PCR_TSUIJI_88_7_116_5_POSTPUBLICATION_G1",
        "INTRADAY_VOLATILITY_HAR_RSV_DI1",
        "INTRADAY_PATH_US_TO_JNU_TRUE_G1",
        "PHASE4B_USDJPY_1D",
        "NEWS_STATE_LANGUAGE_SOURCE_G1",
        "BOJ_MPM_TRUE_OSE_EVENT_VOLATILITY_G1",
    }
    ledger_missing=sorted(ledger_required-ids)

    validated_directional=int(current["validated_modules"]["directional_modules"])
    decision=current["validated_modules"]["decision_engine_direction"]
    decision_consistent=(
        (validated_directional==0 and decision=="NO_VALIDATED_DIRECTIONAL_EDGE")
        or (validated_directional>0 and decision!="NO_VALIDATED_DIRECTIONAL_EDGE")
    )

    stage9_validated=sum(
        1 for x in stage9["modules"].values()
        if x["status"]=="VALIDATED_JNU_MODULE_ROLE_CONSTRAINED"
    )

    hard_checks={
        "exactly_8_major_candidates": len(expected)==8,
        "all_major_candidates_terminal": len(missing)==0,
        "permanent_ledger_required_entries_present": len(ledger_missing)==0,
        "decision_engine_direction_consistent": decision_consistent,
        "stage9_has_no_pending_gate": all(
            x["status"]!="STAGE9_BLOCKED_STAGE8_PENDING" for x in stage9["modules"].values()
        ),
        "current_status_artifact_role_separation": current["validated_modules"]["decision_engine_direction"]==decision,
        "required_reproducibility_artifacts_present": all(p.exists() for p in [CRITERIA,LEDGER,GAP,CURRENT,STAGE9]),
    }

    if not hard_checks["all_major_candidates_terminal"] or not hard_checks["stage9_has_no_pending_gate"]:
        status="FRAMEWORK_INCOMPLETE_PENDING_MAJOR_CANDIDATES"
    elif not all(hard_checks.values()):
        status="FRAMEWORK_COMPLETION_AUDIT_FAIL_CLOSED"
    elif validated_directional>0:
        status="FRAMEWORK_COMPLETE_WITH_VALIDATED_EDGE"
    else:
        status="FRAMEWORK_COMPLETE_NO_VALIDATED_DIRECTIONAL_EDGE"

    result={
        "version":"1.0",
        "status":status,
        "prereg_sha256":sha256_file(PREREG),
        "major_candidates_total":8,
        "major_candidates_terminal":len(dispositions),
        "major_candidates_pending":missing,
        "major_candidate_dispositions":dispositions,
        "hard_checks":hard_checks,
        "ledger_missing_required_entries":ledger_missing,
        "validated_role_constrained_stage9_modules":stage9_validated,
        "validated_directional_modules":validated_directional,
        "decision_engine_direction":decision,
        "completion_allowed": status in {
            "FRAMEWORK_COMPLETE_WITH_VALIDATED_EDGE",
            "FRAMEWORK_COMPLETE_NO_VALIDATED_DIRECTIONAL_EDGE",
        },
        "artifact_hashes":{
            "completion_criteria":sha256_file(CRITERIA),
            "family_attempt_ledger":sha256_file(LEDGER),
            "completion_gap":sha256_file(GAP),
            "current_framework_status":sha256_file(CURRENT),
            "stage9_review":sha256_file(STAGE9),
        },
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
    }

    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[
        "# JNU Final Framework Completion Audit v1",
        "",
        f"- Status: **{status}**",
        f"- Major candidates terminal: **{len(dispositions)} / 8**",
        f"- Pending: **{', '.join(missing) if missing else 'NONE'}**",
        f"- Validated Stage9 role-constrained modules: **{stage9_validated}**",
        f"- Validated directional modules: **{validated_directional}**",
        f"- Direction engine: **{decision}**",
        f"- Completion allowed: **{result['completion_allowed']}**",
        "",
        "## Hard checks",
    ]
    lines.extend(f"- {k}: **{v}**" for k,v in hard_checks.items())
    REPORT.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
