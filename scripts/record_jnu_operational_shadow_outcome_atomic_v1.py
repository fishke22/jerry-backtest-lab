from __future__ import annotations
import argparse, json, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RECORDER=ROOT/"scripts"/"record_jnu_operational_shadow_outcome_v1.py"
DEFAULT_FORECAST=ROOT/"live_shadow"/"forecasts"
DEFAULT_OUTCOME=ROOT/"live_shadow"/"outcomes"

def run(cmd:list[str],cwd:Path=ROOT)->subprocess.CompletedProcess:
    return subprocess.run(cmd,cwd=cwd,check=True,capture_output=True,text=True)

def git_staging_empty()->bool:
    return run(["git","diff","--cached","--name-only"]).stdout.strip()==""

def tracked_clean(path:Path)->None:
    rel=path.relative_to(ROOT).as_posix()
    run(["git","ls-files","--error-unmatch",rel])
    dirty=run(["git","status","--porcelain","--",rel]).stdout.strip()
    if dirty:
        raise RuntimeError(f"forecast file must be committed and clean before outcome recording: {dirty}")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--forecast-id",required=True)
    ap.add_argument("--target-close-price",type=float,required=True)
    ap.add_argument("--target-close-timestamp",required=True)
    ap.add_argument("--target-close-source",required=True)
    ap.add_argument("--exact-product",action="store_true")
    ap.add_argument("--forecast-dir",type=Path,default=DEFAULT_FORECAST)
    ap.add_argument("--outcome-dir",type=Path,default=DEFAULT_OUTCOME)
    ap.add_argument("--commit-push",action="store_true")
    args=ap.parse_args()

    real=args.forecast_dir.resolve()==DEFAULT_FORECAST.resolve() and args.outcome_dir.resolve()==DEFAULT_OUTCOME.resolve()
    fp=args.forecast_dir/f"{args.forecast_id}.json"
    if not fp.exists():
        raise RuntimeError("forecast record not found")
    if real:
        if not args.commit_push:
            raise RuntimeError("real outcome recording requires --commit-push")
        if not git_staging_empty():
            raise RuntimeError("Git staging area must be empty before real outcome recording")
        tracked_clean(fp)

    with tempfile.TemporaryDirectory(prefix="jnu_shadow_outcome_") as td:
        tmpout=Path(td)/"outcomes"
        cp=run([
            sys.executable,str(RECORDER),
            "--forecast-id",args.forecast_id,
            "--target-close-price",str(args.target_close_price),
            "--target-close-timestamp",args.target_close_timestamp,
            "--target-close-source",args.target_close_source,
            "--forecast-dir",str(args.forecast_dir),
            "--outcome-dir",str(tmpout),
            *(["--exact-product"] if args.exact_product else [])
        ])
        info=json.loads(cp.stdout)
        src=Path(info["path"])
        args.outcome_dir.mkdir(parents=True,exist_ok=True)
        dst=args.outcome_dir/f"{args.forecast_id}.json"
        if dst.exists():
            raise RuntimeError(f"outcome already exists in destination: {dst}")
        shutil.copy2(src,dst)

    commit_sha=None
    try:
        if real:
            rel=dst.relative_to(ROOT).as_posix()
            run(["git","add","--",rel])
            staged=run(["git","diff","--cached","--name-only"]).stdout.strip().splitlines()
            if staged!=[rel]:
                raise RuntimeError(f"unexpected staged files during outcome registration: {staged}")
            run(["git","commit","-m",f"Record JNU live-shadow outcome {args.forecast_id}"])
            commit_sha=run(["git","rev-parse","HEAD"]).stdout.strip()
            run(["git","push","origin","main"])
            dirty=run(["git","status","--porcelain","--",rel]).stdout.strip()
            if dirty:
                raise RuntimeError(f"registered outcome is dirty after commit: {dirty}")
        print(json.dumps({
            "status":"OUTCOME_RECORDED_ATOMIC_COMMITTED" if real else "OUTCOME_RECORDED_ATOMIC_SELFTEST",
            "forecast_id":args.forecast_id,
            "outcome_return":info["outcome_return"],
            "directional_hit":info["directional_hit"],
            "path":str(dst),
            "git_commit":commit_sha
        },ensure_ascii=False,indent=2))
    except Exception:
        if real:
            subprocess.run(["git","reset","HEAD","--",str(dst.relative_to(ROOT).as_posix())],cwd=ROOT,capture_output=True,text=True)
            if dst.exists():
                dst.unlink()
        raise

if __name__=="__main__":
    main()
