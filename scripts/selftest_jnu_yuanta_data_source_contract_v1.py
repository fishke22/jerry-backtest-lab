from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

def main() -> int:
    fallback = load("config/jnu_data_source_fallback_v1.json")
    feed = load("config/jnu_yuanta_readonly_feed_v1.json")
    evidence = load("config/jnu_yuanta_feed_capability_evidence_20260926_v1.json")

    checks = {
        "exact_live_quote_verified": evidence["evidence_summary"]["exact_live_quote"]["status"] == "VERIFIED",
        "exact_quote_matches_market_207": evidence["evidence_summary"]["exact_live_quote"]["market_no"] == 207,
        "tick_detail_data_return_verified": evidence["evidence_summary"]["current_day_tick_detail"]["status"].startswith("VERIFIED_DATA_RETURN"),
        "l2_not_promoted": "UNVERIFIED" in evidence["evidence_summary"]["five_ten_level_depth"]["status"],
        "streaming_tick_not_promoted": "UNVERIFIED" in evidence["evidence_summary"]["streaming_ticks"]["status"],
        "fallback_exact_quote_verified": "LIVE_CALLBACK_VERIFIED" in fallback["local_bridge"]["observed_state_20260926"]["ose_subscription"],
        "fallback_l2_unverified": "UNVERIFIED" in fallback["local_bridge"]["observed_state_20260926"]["l2_depth"],
        "feed_exact_quote_verified": feed["verified_account_capabilities"]["exact_live_quote"].startswith("VERIFIED"),
        "feed_l2_unverified": "UNVERIFIED" in feed["verified_account_capabilities"]["five_ten_level_depth"],
        "single_owner_required": feed["single_owner_rule"].startswith("Never create a second Yuanta broker login"),
        "no_double_login_fallback": fallback["no_double_login_rule"].startswith("When MARKET_AI_HUB is available"),
        "permanent_free_l2_not_found": fallback["free_data_research_result"]["permanent_free_legal_exact_ose_realtime_l2_found"] is False,
        "orders_prohibited": "all order placement" in feed["prohibited_calls"],
    }
    failed = [k for k,v in checks.items() if not v]
    print(json.dumps({
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed": failed,
        "broker_call_performed": False
    }, indent=2))
    return 0 if not failed else 1

if __name__ == "__main__":
    raise SystemExit(main())
