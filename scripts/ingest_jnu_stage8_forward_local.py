from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAR_BUILDER = ROOT / "scripts" / "build_225labo_micro_rvrsv_local.py"
BOJ_BUILDER = ROOT / "scripts" / "build_225labo_boj_mpm_event_volatility_local.py"
CALENDAR = ROOT / "config" / "jnu_session_calendar_versions.json"
EVENTS = ROOT / "event_data" / "boj" / "boj_mpm_eligible_event_windows_v1.json"
HAR_REPO_PANEL = ROOT / "cloud_data" / "derived" / "jnu_225labo_micro_daily_rvrsv_v1.csv"
HAR_REPO_MANIFEST = ROOT / "cloud_data" / "manifests" / "jnu_225labo_micro_daily_rvrsv_v1_manifest.json"
BOJ_REPO_PANEL = ROOT / "cloud_data" / "derived" / "jnu_boj_mpm_micro_event_volatility_g1.csv"
BOJ_REPO_MANIFEST = ROOT / "cloud_data" / "manifests" / "jnu_boj_mpm_micro_event_volatility_g1_manifest.json"
READINESS = ROOT / "scripts" / "check_jnu_stage8_readiness_v1.py"


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_last_touch(path: Path) -> str:
    rel=path.relative_to(ROOT).as_posix()
    cp=subprocess.run(
        ["git","log","-1","--format=%H","--",rel],
        cwd=ROOT,check=True,capture_output=True,text=True,
    )
    sha=cp.stdout.strip()
    if len(sha)!=40:
        raise RuntimeError(f"could not resolve last-touch commit for {rel}")
    return sha


def source_hashes(raw_dir: Path) -> dict[str,str]:
    files=sorted(raw_dir.glob("N225microf_*.zip"))
    if not files:
        raise RuntimeError(f"no N225microf_*.zip files found under {raw_dir}")
    return {p.name:sha256_file(p) for p in files}


def manifest_source_hashes(manifest: dict) -> dict[str,str]:
    rows=manifest.get("source_hashes")
    if not isinstance(rows,list):
        raise RuntimeError("manifest source_hashes missing")
    return {str(x["source_id"]):str(x["sha256"]) for x in rows}


def validate_safe_derived(panel: Path, manifest_path: Path) -> dict:
    m=load_json(manifest_path)
    if m.get("raw_data_cloud_uploaded") is not False:
        raise RuntimeError("safe-derived validation failed: raw_data_cloud_uploaded must be false")
    if m.get("critical_data_quality_issues") != []:
        raise RuntimeError(f"safe-derived validation failed: critical DQ {m.get('critical_data_quality_issues')}")
    got=sha256_file(panel)
    if m.get("derived_output_hash") != got:
        raise RuntimeError("safe-derived validation failed: derived hash mismatch")
    return m


def run_checked(cmd: list[str]) -> None:
    print("RUN", " ".join(cmd), flush=True)
    subprocess.run(cmd,cwd=ROOT,check=True)


def copy_safe(src: Path,dst: Path) -> None:
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst)


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw-dir",type=Path,required=True,help="Local-only personally licensed 225Labo Micro raw directory.")
    ap.add_argument("--work-dir",type=Path,required=True,help="Local-only staging directory for regenerated safe derived outputs.")
    ap.add_argument("--apply",action="store_true",help="Regenerate/copy safe derived panels when source or event manifest changed. Default is check-only.")
    ap.add_argument("--status-output",type=Path,default=None,help="Optional non-sensitive JSON status output.")
    args=ap.parse_args()

    raw_dir=args.raw_dir.resolve()
    work_dir=args.work_dir.resolve()
    current_raw=source_hashes(raw_dir)
    har_manifest=load_json(HAR_REPO_MANIFEST)
    boj_manifest=load_json(BOJ_REPO_MANIFEST)
    har_prior=manifest_source_hashes(har_manifest)
    boj_prior=manifest_source_hashes(boj_manifest)
    event_hash=sha256_file(EVENTS)
    prior_event_hash=str(boj_manifest.get("event_manifest_sha256") or "")

    raw_changed=(current_raw != har_prior) or (current_raw != boj_prior)
    event_changed=event_hash != prior_event_hash
    changed_files=sorted({
        name for name in set(current_raw)|set(har_prior)|set(boj_prior)
        if current_raw.get(name)!=har_prior.get(name) or current_raw.get(name)!=boj_prior.get(name)
    })

    base={
        "version":"1.0",
        "mode":"APPLY" if args.apply else "CHECK_ONLY",
        "raw_package_count":len(current_raw),
        "raw_changed":raw_changed,
        "event_manifest_changed":event_changed,
        "changed_source_ids":changed_files,
        "har_builder_commit":git_last_touch(HAR_BUILDER),
        "boj_builder_commit":git_last_touch(BOJ_BUILDER),
        "raw_data_cloud_uploaded":False,
        "credentials_or_download_performed":False,
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
    }

    if not raw_changed and not event_changed:
        result={
            **base,
            "status":"NO_SOURCE_CHANGE",
            "derived_panels_modified":False,
            "readiness_rerun":False,
            "next_action":"No action. Replace/update the local licensed source package manually when authorized new data is available, then rerun check-only before --apply.",
        }
        text=json.dumps(result,ensure_ascii=False,indent=2)
        print(text)
        if args.status_output:
            args.status_output.parent.mkdir(parents=True,exist_ok=True)
            args.status_output.write_text(text+"\n",encoding="utf-8")
        return

    if not args.apply:
        result={
            **base,
            "status":"SOURCE_CHANGE_DETECTED_APPLY_REQUIRED",
            "derived_panels_modified":False,
            "readiness_rerun":False,
            "next_action":"Review source/event changes, then rerun the same command with --apply. No outcome metrics are inspected by this orchestrator.",
        }
        text=json.dumps(result,ensure_ascii=False,indent=2)
        print(text)
        if args.status_output:
            args.status_output.parent.mkdir(parents=True,exist_ok=True)
            args.status_output.write_text(text+"\n",encoding="utf-8")
        return

    work_dir.mkdir(parents=True,exist_ok=True)
    changed_outputs=[]

    if raw_changed:
        har_out=work_dir/"har_rsv"
        if har_out.exists():
            shutil.rmtree(har_out)
        har_out.mkdir(parents=True)
        run_checked([
            sys.executable,str(HAR_BUILDER),
            "--input-dir",str(raw_dir),
            "--calendar",str(CALENDAR),
            "--output-dir",str(har_out),
            "--skip-1m-qa",
            "--parser-commit",git_last_touch(HAR_BUILDER),
        ])
        hp=har_out/"jnu_225labo_micro_daily_rvrsv_v1.csv"
        hm=har_out/"jnu_225labo_micro_daily_rvrsv_v1_manifest.json"
        validate_safe_derived(hp,hm)
        copy_safe(hp,HAR_REPO_PANEL)
        copy_safe(hm,HAR_REPO_MANIFEST)
        changed_outputs += [str(HAR_REPO_PANEL.relative_to(ROOT)),str(HAR_REPO_MANIFEST.relative_to(ROOT))]

    if raw_changed or event_changed:
        boj_out=work_dir/"boj_mpm"
        if boj_out.exists():
            shutil.rmtree(boj_out)
        boj_out.mkdir(parents=True)
        run_checked([
            sys.executable,str(BOJ_BUILDER),
            "--product","MICRO",
            "--input-dir",str(raw_dir),
            "--events",str(EVENTS),
            "--output-dir",str(boj_out),
            "--parser-commit",git_last_touch(BOJ_BUILDER),
        ])
        bp=boj_out/"jnu_boj_mpm_micro_event_volatility_g1.csv"
        bm=boj_out/"jnu_boj_mpm_micro_event_volatility_g1_manifest.json"
        validate_safe_derived(bp,bm)
        copy_safe(bp,BOJ_REPO_PANEL)
        copy_safe(bm,BOJ_REPO_MANIFEST)
        changed_outputs += [str(BOJ_REPO_PANEL.relative_to(ROOT)),str(BOJ_REPO_MANIFEST.relative_to(ROOT))]

    run_checked([sys.executable,str(READINESS)])
    result={
        **base,
        "status":"SAFE_DERIVED_REBUILT_READINESS_RERUN",
        "derived_panels_modified":True,
        "changed_outputs":changed_outputs,
        "readiness_rerun":True,
        "performance_metrics_computed":False,
        "next_action":"Inspect only the readiness result. Do not run Stage8 outcome unless readiness is READY_TO_RUN_STAGE8.",
    }
    text=json.dumps(result,ensure_ascii=False,indent=2)
    print(text)
    if args.status_output:
        args.status_output.parent.mkdir(parents=True,exist_ok=True)
        args.status_output.write_text(text+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
