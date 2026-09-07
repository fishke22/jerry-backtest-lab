from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
A=json.loads((ROOT/"config"/"jnu_operational_framework_current_v1_8.json").read_text(encoding="utf-8"))
B=json.loads((ROOT/"config"/"jnu_operational_framework_current_v1_9.json").read_text(encoding="utf-8"))
same_keys=["validation_taxonomy","layers","current_validated_state_modules","prohibited_directional_families","current_directional_status","prediction_discipline","directional_research_gate","operational_decision_protocol"]
tests={}
for k in same_keys:
    tests["unchanged_"+k]=(A[k]==B[k])
tests["version_1_9"]=B["version"]=="1.9"
tests["supersedes_v1_8"]=B["supersedes"]=="config/jnu_operational_framework_current_v1_8.json"
tests["directional_semantics_flag"]=B.get("directional_semantics_unchanged_from_v1_8") is True
tests["blocker"]=B["exact_micro_reference_source"]["current_blocker"]=="LICENSED_REALTIME_ENTITLEMENT_REQUIRED_FOR_RELIABLE_SUB900_PATH"
tests["freshness_900"]=B["exact_micro_reference_source"]["frozen_maximum_provider_timestamp_age_seconds"]==900
tests["continuous_prohibited"]=B["exact_micro_reference_source"]["continuous_contract_primary_prohibited"] is True
tests["broker_feed_prohibited"]=B["exact_micro_reference_source"]["authorized_read_only_broker_feed"]=="PROHIBITED_UNTIL_EXPLICIT_GOVERNANCE_AMENDMENT"
tests["validated_directional_zero"]=B["source_governance"]["validated_directional_modules"]==0
tests["real_ledger_zero"]=B["source_governance"]["real_ledger"]=={"forecasts":0,"outcomes":0}
status="PASS" if all(tests.values()) else "FAIL"
print(json.dumps({"status":status,"tests":tests,"passed":sum(tests.values()),"total":len(tests)},indent=2))
raise SystemExit(0 if status=="PASS" else 1)
