from __future__ import annotations
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from fetch_jnu_official_event_state_v1 import (
    TOKYO,EASTERN,TAIPEI,
    event,evaluate_event_state,
    parse_boj,parse_stat_single_release,parse_esri_general,parse_esri_gdp,
    parse_bea,parse_fed,parse_bls,
)

TARGET=date(2026,9,7)
URL="https://official.example/selftest"

def check(name,cond):
    if not cond:
        raise RuntimeError(f"SELFTEST_FAIL:{name}")
    return True

def main():
    tests={}
    boj='''<table><tr><th>Date</th><th>Time</th><th>Title</th></tr>
    <tr><td>Sept. 7</td><td>10:30</td><td>Speech by Board Member TEST at a meeting with local leaders</td></tr>
    <tr><td></td><td>14:00</td><td>Consumption Activity Index</td></tr></table>'''
    x=parse_boj(boj,TARGET,URL)
    tests["boj_parser"]=check("boj_parser",len(x)==2 and x[0]["impact"]=="HIGH" and x[1]["impact"]=="CONTEXT")

    stat='''<table><tr><th>Reference month</th><th>Date of release</th></tr>
    <tr><td>August</td><td>September 7</td></tr></table>'''
    x=parse_stat_single_release(stat,TARGET,URL,"JAPAN_STAT_CPI","National Consumer Price Index")
    tests["stat_parser"]=check("stat_parser",len(x)==1 and x[0]["event_date"]=="2026-09-07" and x[0]["impact"]=="HIGH")

    esri='''<table><tr><th>Indexes of Business Conditions (Preliminary Release)</th><th>Machinery Orders</th><th>Business Outlook Survey</th></tr>
    <tr><td>Sep.7,2026 (Jul.)</td><td>Sep.16,2026 (Jul.)</td><td>Sep.11,2026 (Jul.-Sep.)</td></tr></table>'''
    x=parse_esri_general(esri,TARGET,URL)
    tests["esri_parser"]=check("esri_parser",len(x)==3 and x[0]["impact"]=="CONTEXT" and x[1]["impact"]=="HIGH")

    gdp='''<table><tr><th>Reporting period</th><th>Release Date</th><th>Time</th></tr>
    <tr><td>Apr.-Jun. 2026 (The Second Preliminary)</td><td>Tuesday, September 8, 2026</td><td>8:50AM (JST)</td></tr></table>'''
    x=parse_esri_gdp(gdp,TARGET,URL)
    tests["gdp_parser"]=check("gdp_parser",len(x)==1 and x[0]["impact"]=="HIGH" and x[0]["scheduled_time"]=="08:50")

    bea='''<table><tr><th>Year 2026</th><th></th><th>Release</th></tr>
    <tr><td>September 7 8:30 AM</td><td>News</td><td>Personal Income and Outlays, August 2026</td></tr></table>'''
    x=parse_bea(bea,TARGET,URL)
    tests["bea_parser"]=check("bea_parser",len(x)==1 and x[0]["impact"]=="HIGH" and x[0]["scheduled_time"]=="08:30")

    fed='''<div class="cal-nojs"><h4>Speeches</h4>
    <div class="panel"><div>8:30 a.m.</div><div>Speech - Governor Test Economic Outlook</div><div>7</div></div>
    <h4>FOMC Meetings</h4><div class="panel"><div>2:00 p.m.</div><div>FOMC Meeting</div><div>16</div></div></div>'''
    x=parse_fed(fed,TARGET,URL)
    tests["fed_parser"]=check("fed_parser",len(x)==2 and all(e["impact"]=="HIGH" for e in x))

    bls='''<table><tr><th>Date</th><th>Time</th><th>Release</th></tr>
    <tr><td>Monday, September 7, 2026</td><td>08:30 AM</td><td>Consumer Price Index for August 2026</td></tr></table>'''
    x=parse_bls(bls,TARGET,URL)
    tests["bls_parser"]=check("bls_parser",len(x)==1 and x[0]["impact"]=="HIGH")

    eval_pre=datetime(2026,9,7,8,0,tzinfo=TAIPEI)
    high_future=[event("X","high",TARGET,time(10,0),TOKYO,"HIGH",URL)]
    state,*_=evaluate_event_state(high_future,[],eval_pre,TARGET)
    tests["pre_release_high"]=check("pre_release_high",state=="PRE_RELEASE_HIGH")

    high_past=[event("X","high",TARGET,time(8,0),TOKYO,"HIGH",URL)]
    state,*_=evaluate_event_state(high_past,[],eval_pre,TARGET)
    tests["post_event_high"]=check("post_event_high",state=="POST_EVENT_HIGH")

    context=[event("X","context",TARGET,time(10,0),TOKYO,"CONTEXT",URL)]
    state,*_=evaluate_event_state(context,[],eval_pre,TARGET)
    tests["normal"]=check("normal",state=="NORMAL")

    state,*_=evaluate_event_state(context,[{"source_id":"BLS","error":"403"}],eval_pre,TARGET)
    tests["source_failure_unknown"]=check("source_failure_unknown",state=="UNKNOWN")

    date_only=[event("X","date only high",TARGET,None,TOKYO,"HIGH",URL)]
    state,*_=evaluate_event_state(date_only,[],eval_pre,TARGET)
    tests["date_only_high_unknown"]=check("date_only_high_unknown",state=="UNKNOWN")

    print({"status":"PASS","tests":tests})

if __name__=="__main__":
    main()
