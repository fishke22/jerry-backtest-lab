from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "config" / "jnu_stage9_role_validation_prereg_v1.json"
HAR_A = ROOT / "volatility_results" / "jnu_har_rsv_true_ose_mini_stage_a_g1.json"
HAR_B = ROOT / "volatility_results" / "jnu_har_rsv_jnu_micro_stage_b_g1.json"
HAR_8 = ROOT / "volatility_results" / "jnu_har_rsv_jnu_micro_stage8_forward_g1.json"
BOJ_A = ROOT / "event_volatility_results" / "jnu_boj_mpm_true_ose_mini_stage_a_g1.json"
BOJ_B = ROOT / "event_volatility_results" / "jnu_boj_mpm_exact_jnu_micro_stage_b_g1.json"
BOJ_8 = ROOT / "event_volatility_results" / "jnu_boj_mpm_stage8_forward_g1.json"
RESULT = ROOT / "stage9_results" / "jnu_stage9_role_validation_v1.json"
REPORT = ROOT / "stage9_reports" / "jnu_stage9_role_validation_v1.md"


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path) -> dict:
    if not path.exists():
        raise RuntimeError(f"missing prerequisite artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def review_module(name: str, stage_a: dict, stage_b: dict, stage8: dict, prereg: dict) -> dict:
    cfg=prereg["modules"][name]
    if name=="HAR_RSV_DI1":
        a_ok=stage_a.get("status")=="TRUE_OSE_MINI_STAGE_A_PASS"
        b_ok=stage_b.get("status")=="TRUE_JNU_MICRO_STAGE_B_PASS"
        pass8="STAGE8_FORWARD_HOLDOUT_PASS"
        fail8="STAGE8_FORWARD_HOLDOUT_FAIL_CURRENT_SPEC"
    else:
        a_ok=stage_a.get("status")=="TRUE_OSE_MINI_BOJ_EVENT_VOL_STAGE_A_PASS"
        b_ok=stage_b.get("status")=="TRUE_JNU_MICRO_BOJ_EVENT_VOL_STAGE_B_PASS"
        pass8="STAGE8_FORWARD_EVENT_HOLDOUT_PASS"
        fail8="STAGE8_FORWARD_EVENT_HOLDOUT_FAIL_CURRENT_SPEC"

    s8=stage8.get("status")
    if not a_ok or not b_ok:
        status="STAGE9_NOT_ADMITTED"
        reason="EARLIER_TRUE_TARGET_PREREQUISITE_NOT_PASS"
    elif s8==pass8:
        status="VALIDATED_JNU_MODULE_ROLE_CONSTRAINED"
        reason="ALL_APPLICABLE_STATISTICAL_STAGE_PREREQUISITES_PASS"
    elif s8==fail8:
        status="STAGE9_NOT_ADMITTED"
        reason="STAGE8_FORWARD_HOLDOUT_FAIL"
    else:
        status="STAGE9_BLOCKED_STAGE8_PENDING"
        reason="STAGE8_FORWARD_HOLDOUT_NOT_TERMINAL"

    return {
        "stage9_id":cfg["stage9_id"],
        "role":cfg["role"],
        "status":status,
        "reason":reason,
        "stage_a_pass":a_ok,
        "stage_b_pass":b_ok,
        "stage8_status":s8,
        "validated_directional_edge":False,
        "allowed_effects":cfg["allowed_effects"] if status=="VALIDATED_JNU_MODULE_ROLE_CONSTRAINED" else [],
        "prohibited":cfg["prohibited"],
    }


def main() -> None:
    pre=load(PREREG)
    har=review_module("HAR_RSV_DI1",load(HAR_A),load(HAR_B),load(HAR_8),pre)
    boj=review_module("BOJ_MPM_EVENT_VOLATILITY_G1",load(BOJ_A),load(BOJ_B),load(BOJ_8),pre)
    modules={"HAR_RSV_DI1":har,"BOJ_MPM_EVENT_VOLATILITY_G1":boj}
    validated=sum(1 for x in modules.values() if x["status"]=="VALIDATED_JNU_MODULE_ROLE_CONSTRAINED")
    result={
        "version":"1.0",
        "prereg_sha256":sha256_file(PREREG),
        "status":"STAGE9_REVIEW_PENDING" if any(x["status"]=="STAGE9_BLOCKED_STAGE8_PENDING" for x in modules.values()) else "STAGE9_REVIEW_TERMINAL",
        "modules":modules,
        "validated_jnu_modules_from_this_review":validated,
        "validated_directional_modules_from_this_review":0,
        "decision_engine_direction":"NO_VALIDATED_DIRECTIONAL_EDGE",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
    }
    RESULT.parent.mkdir(parents=True,exist_ok=True)
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# JNU Stage9 role validation v1","",f"- Status: **{result['status']}**",f"- Validated role-constrained JNU modules: **{validated}**","- Validated directional modules: **0**","- Direction engine: **NO_VALIDATED_DIRECTIONAL_EDGE**",""]
    for k,v in modules.items():
        lines += [f"## {k}",f"- Stage9 status: **{v['status']}**",f"- Role: {v['role']}",f"- Stage8: {v['stage8_status']}",""]
    REPORT.write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
