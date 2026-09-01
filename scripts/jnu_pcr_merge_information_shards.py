from __future__ import annotations

import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PREREG=ROOT/"config"/"jnu_pcr_full_information_panel_prereg_v1.json"
INROOT=Path(os.environ.get("PCR_SHARDS_DIR", str(ROOT/"pcr_shards")))
OUT=ROOT/"pcr_results"/"jnu_pcr_full_information_panel_v1.json"
REPORT=ROOT/"pcr_reports"/"jnu_pcr_full_information_panel_v1.md"

def main():
    prereg=json.loads(PREREG.read_text(encoding="utf-8"))
    files=sorted(INROOT.rglob("jnu_pcr_information_panel_v1.json"))
    if len(files)!=len(prereg["shards"]):
        raise RuntimeError("unexpected shard file count: "+str(len(files)))

    months=[]
    shard_meta=[]
    for p in files:
        d=json.loads(p.read_text(encoding="utf-8"))
        if d.get("directional_return_outcomes_used") is not False:
            raise RuntimeError("directional-return contamination")
        if d.get("formal_directional_family_opened") is not False:
            raise RuntimeError("formal-family contamination")
        shard_meta.append({
            "path":str(p.relative_to(INROOT)),
            "year_range":d.get("year_range"),
            "status_counts":d.get("status_counts",{}),
            "month_count":len(d.get("months",[])),
        })
        months.extend(d.get("months",[]))

    months=sorted(months,key=lambda x:x["month"])
    names=[m["month"] for m in months]
    if len(names)!=len(set(names)):
        raise RuntimeError("duplicate months")
    gate=prereg["data_feasibility_gate"]
    if len(months)!=gate["expected_manifest_months"]:
        raise RuntimeError("unexpected month count: "+str(len(months)))

    status_counts={}
    for m in months:
        status_counts[m["status"]]=status_counts.get(m["status"],0)+1

    parser_errors=[m["month"] for m in months if m["status"]=="PARSER_OR_SOURCE_ERROR"]
    archive_incomplete=[m["month"] for m in months if m["status"]=="ARCHIVE_INCOMPLETE"]
    defined=[m for m in months if m["status"]=="PCR_DEFINED"]
    undefined=[m for m in months if m["status"]=="PCR_UNDEFINED_REQUIRED_DAY"]
    archive_complete=[m for m in months if m["status"]!="ARCHIVE_INCOMPLETE"]
    recent36=archive_complete[-36:]
    recent_defined=[m for m in recent36 if m["status"]=="PCR_DEFINED"]

    checks={
        "manifest_month_count_match":len(months)==gate["expected_manifest_months"],
        "archive_complete_count_match":len(archive_complete)==gate["expected_archive_complete_months"],
        "known_archive_incomplete_months_match":archive_incomplete==gate["known_archive_incomplete_months"],
        "zero_unexpected_parser_or_source_errors":len(parser_errors)==gate["unexpected_parser_or_source_errors_allowed"],
        "minimum_total_defined_months":len(defined)>=gate["minimum_pcr_defined_months"],
        "minimum_total_defined_fraction":(len(defined)/len(archive_complete))>=gate["minimum_total_defined_fraction_of_archive_complete"],
        "minimum_recent_defined_months":len(recent_defined)>=gate["minimum_recent_defined_months"],
        "minimum_recent_defined_fraction":(len(recent_defined)/len(recent36))>=gate["minimum_recent_defined_fraction"],
    }
    passed=all(checks.values())

    undefined_days=[]
    for m in undefined:
        for d in m.get("days",[]):
            if d.get("undefined_reason"):
                undefined_days.append({"month":m["month"],"date":d["date"],"reason":d["undefined_reason"]})

    result={
        "version":"1.0",
        "as_of":"2026-09-01",
        "candidate_id":prereg["candidate_id"],
        "status":prereg["classification"]["pass"] if passed else prereg["classification"]["fail_or_inconclusive"],
        "data_feasibility_pass":passed,
        "directional_return_outcomes_used":False,
        "formal_directional_family_opened":False,
        "alpha_evidence":False,
        "preregistration":"config/jnu_pcr_full_information_panel_prereg_v1.json",
        "shards":shard_meta,
        "status_counts":status_counts,
        "checks":checks,
        "metrics":{
            "months_total":len(months),
            "archive_complete_months":len(archive_complete),
            "pcr_defined_months":len(defined),
            "pcr_undefined_required_day_months":len(undefined),
            "archive_incomplete_months":len(archive_incomplete),
            "parser_or_source_error_months":len(parser_errors),
            "defined_fraction_of_archive_complete":len(defined)/len(archive_complete),
            "recent36_defined_months":len(recent_defined),
            "recent36_defined_fraction":len(recent_defined)/len(recent36),
        },
        "archive_incomplete_months":archive_incomplete,
        "parser_or_source_error_months":parser_errors,
        "undefined_days":undefined_days,
        "months":months,
    }

    OUT.parent.mkdir(exist_ok=True)
    REPORT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=[
        "# JNU PCR full information panel v1",
        "",
        "- Status: **"+result["status"]+"**",
        "- Data feasibility PASS: **"+str(passed)+"**",
        "- Directional return outcomes used: **false**",
        "- Formal directional family opened: **false**",
        "- Status counts: "+json.dumps(status_counts,ensure_ascii=False),
        "- Defined months: **"+str(len(defined))+" / "+str(len(archive_complete))+"** archive-complete",
        "- Recent 36 defined: **"+str(len(recent_defined))+" / "+str(len(recent36))+"**",
        "- Parser/source errors: **"+str(len(parser_errors))+"**",
        "- Undefined required-day months: **"+str(len(undefined))+"**",
        "",
    ]
    REPORT.write_text("\n".join(lines),encoding="utf-8")
    print(json.dumps({"status":result["status"],"metrics":result["metrics"],"checks":checks},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
