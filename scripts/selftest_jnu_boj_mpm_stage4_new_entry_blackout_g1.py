from __future__ import annotations

import json
from datetime import datetime, timedelta, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PREREG=ROOT/"config"/"jnu_boj_mpm_stage4_new_entry_blackout_g1_prereg.json"
CORPUS=ROOT/"event_data"/"boj"/"boj_mpm_release_times_post_mini_launch_v1.json"
RESULT=ROOT/"stage4_results"/"jnu_boj_mpm_stage4_new_entry_blackout_g1_selftest.json"
REPORT=ROOT/"stage4_reports"/"jnu_boj_mpm_stage4_new_entry_blackout_g1_selftest.md"

def tod(s:str)->time:
    h,m=map(int,s.split(":"))
    return time(h,m)

def dt(date_s:str,time_s:str)->datetime:
    return datetime.fromisoformat(date_s+"T"+time_s)

def blackout_end(release_observed_at:datetime|None, session_close:datetime)->datetime:
    if release_observed_at is None:
        return session_close
    return min(release_observed_at+timedelta(minutes=20),session_close)

def is_blackout(*,scheduled_mpm_day:bool,ts:datetime,release_observed_at:datetime|None,session_close:datetime)->bool:
    if not scheduled_mpm_day:
        return False
    start=ts.replace(hour=11,minute=0,second=0,microsecond=0)
    return start <= ts < blackout_end(release_observed_at,session_close)

def overlay_target(*,scheduled_mpm_day:bool,ts:datetime,release_observed_at:datetime|None,session_close:datetime,current:int,target:int)->tuple[int,str]:
    if not is_blackout(scheduled_mpm_day=scheduled_mpm_day,ts=ts,release_observed_at=release_observed_at,session_close=session_close):
        return target,"PASS_OUTSIDE_BLACKOUT"
    if target==current:
        return target,"PASS_NO_CHANGE"
    if current==0:
        if target==0:
            return 0,"PASS_FLAT"
        return 0,"SUPPRESS_NEW_EXPOSURE"
    if target==0:
        return 0,"PASS_EXIT"
    # Same-side increase/decrease.
    if current*target>0:
        if abs(target)>abs(current):
            return current,"SUPPRESS_EXPOSURE_INCREASE"
        return target,"PASS_RISK_REDUCTION"
    # Reversal: allow only the closing leg to flat.
    return 0,"CLAMP_REVERSAL_TO_FLAT"

def cancel_outstanding_at_start(*,scheduled_mpm_day:bool,ts:datetime,current:int,order_target:int)->bool:
    if not scheduled_mpm_day or ts.time()!=time(11,0):
        return False
    return abs(order_target)>abs(current) or (current!=0 and order_target*current<0)

def run_case(name,got,expected):
    return {"name":name,"got":got,"expected":expected,"pass":got==expected}

def main():
    prereg=json.loads(PREREG.read_text(encoding="utf-8"))
    assert prereg["candidate_id"]=="BOJ_MPM_STAGE4_NEW_ENTRY_BLACKOUT_G1"
    assert prereg["status"]=="PREREGISTERED_BEFORE_STAGE4_EXECUTION_REPLAY"

    day="2025-01-24"
    release=dt(day,"12:23")
    close=dt(day,"15:45")
    cases=[]
    cases.append(run_case("non_mpm_passthrough",overlay_target(scheduled_mpm_day=False,ts=dt(day,"12:00"),release_observed_at=None,session_close=close,current=0,target=1),(1,"PASS_OUTSIDE_BLACKOUT")))
    cases.append(run_case("mpm_before_1100_passthrough",overlay_target(scheduled_mpm_day=True,ts=dt(day,"10:59"),release_observed_at=None,session_close=close,current=0,target=1),(1,"PASS_OUTSIDE_BLACKOUT")))
    cases.append(run_case("mpm_at_1100_suppress_entry",overlay_target(scheduled_mpm_day=True,ts=dt(day,"11:00"),release_observed_at=None,session_close=close,current=0,target=1),(0,"SUPPRESS_NEW_EXPOSURE")))
    cases.append(run_case("inside_blackout_exit_passes",overlay_target(scheduled_mpm_day=True,ts=dt(day,"12:00"),release_observed_at=None,session_close=close,current=1,target=0),(0,"PASS_EXIT")))
    cases.append(run_case("inside_blackout_reduce_passes",overlay_target(scheduled_mpm_day=True,ts=dt(day,"12:00"),release_observed_at=None,session_close=close,current=2,target=1),(1,"PASS_RISK_REDUCTION")))
    cases.append(run_case("inside_blackout_add_suppressed",overlay_target(scheduled_mpm_day=True,ts=dt(day,"12:00"),release_observed_at=None,session_close=close,current=1,target=2),(1,"SUPPRESS_EXPOSURE_INCREASE")))
    cases.append(run_case("inside_blackout_reversal_flat_only",overlay_target(scheduled_mpm_day=True,ts=dt(day,"12:00"),release_observed_at=None,session_close=close,current=1,target=-1),(0,"CLAMP_REVERSAL_TO_FLAT")))
    cases.append(run_case("release_plus_19m_still_blocked",overlay_target(scheduled_mpm_day=True,ts=dt(day,"12:42"),release_observed_at=release,session_close=close,current=0,target=1),(0,"SUPPRESS_NEW_EXPOSURE")))
    cases.append(run_case("release_plus_20m_unblocked",overlay_target(scheduled_mpm_day=True,ts=dt(day,"12:43"),release_observed_at=release,session_close=close,current=0,target=1),(1,"PASS_OUTSIDE_BLACKOUT")))
    cases.append(run_case("missing_release_blocks_to_close_minus_1m",overlay_target(scheduled_mpm_day=True,ts=dt(day,"15:44"),release_observed_at=None,session_close=close,current=0,target=1),(0,"SUPPRESS_NEW_EXPOSURE")))
    cases.append(run_case("cancel_outstanding_entry_at_1100",cancel_outstanding_at_start(scheduled_mpm_day=True,ts=dt(day,"11:00"),current=0,order_target=1),True))
    cases.append(run_case("do_not_cancel_exit_order",cancel_outstanding_at_start(scheduled_mpm_day=True,ts=dt(day,"11:00"),current=1,order_target=0),False))
    # Summary/Minutes at 08:50 must not be treated as policy decision. The replay
    # simply leaves release_observed_at unset.
    cases.append(run_case("summary_0850_does_not_release_blackout",overlay_target(scheduled_mpm_day=True,ts=dt(day,"11:30"),release_observed_at=None,session_close=close,current=0,target=1),(0,"SUPPRESS_NEW_EXPOSURE")))
    # G1 explicitly excludes unscheduled meetings from the scheduled-date overlay.
    cases.append(run_case("unscheduled_mpm_out_of_scope_passthrough",overlay_target(scheduled_mpm_day=False,ts=dt("2020-05-22","11:00"),release_observed_at=dt("2020-05-22","10:01"),session_close=dt("2020-05-22","15:15"),current=0,target=1),(1,"PASS_OUTSIDE_BLACKOUT")))

    corpus=json.loads(CORPUS.read_text(encoding="utf-8"))
    unscheduled={"2020-03-16","2020-05-22"}
    regular=[]
    for e in corpus["events"]:
        if e["year"]>=2016 and e["date"] not in unscheduled:
            h,m=map(int,e["release_time_jst"].split(":"))
            regular.append((e["date"],h*60+m))
    vals=sorted(v for _,v in regular)
    def q(p):
        z=(len(vals)-1)*p
        lo=int(z); hi=min(lo+1,len(vals)-1); f=z-lo
        return vals[lo]*(1-f)+vals[hi]*f
    meta={
      "n":len(vals),
      "earliest_minute":vals[0],
      "p05_minute":q(.05),
      "median_minute":q(.5),
      "p90_minute":q(.9),
      "latest_minute":vals[-1],
      "all_at_or_after_1100":all(v>=11*60 for v in vals),
      "price_outcomes_used":False
    }
    meta_pass=(
      meta["n"]==84 and meta["earliest_minute"]==11*60+25 and
      round(meta["p05_minute"])==11*60+39 and round(meta["median_minute"])==12*60 and
      round(meta["p90_minute"])==12*60+35 and meta["latest_minute"]==13*60+18 and
      meta["all_at_or_after_1100"] and meta["price_outcomes_used"] is False
    )
    cases.append(run_case("historical_release_metadata_qa",meta_pass,True))

    passed=all(c["pass"] for c in cases)
    result={
      "candidate_id":prereg["candidate_id"],
      "status":"STAGE4_IMPLEMENTATION_SELFTEST_PASS" if passed else "STAGE4_IMPLEMENTATION_SELFTEST_FAIL",
      "promotion_pipeline_stage":4,
      "engineering_selftest_only":True,
      "formal_stage5_independent_replay_pass":False,
      "alpha_or_utility_evidence":False,
      "case_count":len(cases),
      "passed_cases":sum(c["pass"] for c in cases),
      "cases":cases,
      "historical_timing_metadata":meta,
      "promotion_ceiling":prereg["promotion_ceiling_without_valid_base_entry"],
      "next_rule":"If PASS, Stage-4 translation implementation is ready for a genuinely independent Stage-5 replay. Do not run PnL/alpha utility tests without a validated base-entry process."
    }
    RESULT.parent.mkdir(exist_ok=True)
    REPORT.parent.mkdir(exist_ok=True)
    RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    REPORT.write_text(
      "# BOJ MPM Stage-4 new-entry blackout G1 engineering selftest\n\n"
      f"- Status: **{result['status']}**\n"
      f"- Cases: {result['passed_cases']}/{result['case_count']}\n"
      f"- Historical regular/scheduled timing sample: {meta['n']} events\n"
      f"- Earliest / median / latest release minute: {meta['earliest_minute']} / {meta['median_minute']} / {meta['latest_minute']}\n"
      "- Price/PnL outcomes used: **false**\n"
      "- Formal Stage-5 independent replay: **not yet passed**\n"
      "- This result is implementation QA only and has no alpha/utility promotion power.\n",
      encoding="utf-8"
    )
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if passed else 1)

if __name__=="__main__":
    main()
