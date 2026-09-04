from __future__ import annotations
import argparse, json, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DECISION=ROOT/"scripts"/"apply_jnu_operational_decision_protocol_v1.py"
REGISTRAR=ROOT/"scripts"/"register_jnu_operational_shadow_forecast_v1_4.py"
DEFAULT_DIR=ROOT/"live_shadow"/"forecasts"

def run(cmd:list[str],cwd:Path=ROOT)->subprocess.CompletedProcess:
    return subprocess.run(cmd,cwd=cwd,check=True,capture_output=True,text=True)

def git_staging_empty()->bool:
    cp=run(["git","diff","--cached","--name-only"])
    return cp.stdout.strip()==""

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,required=True,help="Forecast envelope with decision_input plus exact JNU reference metadata.")
    ap.add_argument("--output-dir",type=Path,default=DEFAULT_DIR)
    ap.add_argument("--commit-push",action="store_true",help="Required for the default real ledger.")
    args=ap.parse_args()

    x=json.loads(args.input.read_text(encoding="utf-8"))
    decision_input=x.get("decision_input")
    if not isinstance(decision_input,dict):
        raise RuntimeError("decision_input object is required")
    real=args.output_dir.resolve()==DEFAULT_DIR.resolve()
    if real and not args.commit_push:
        raise RuntimeError("real ledger registration requires --commit-push")
    if real and not git_staging_empty():
        raise RuntimeError("Git staging area must be empty before real forecast registration")

    envelope={k:v for k,v in x.items() if k!="decision_input"}
    required=["created_at_taipei","reference_price","reference_timestamp","reference_source","exact_product",
              "target_day_session_date","expected_path","key_levels","invalidation_conditions","event_risk",
              "flip_conditions","evidence_summary"]
    missing=[k for k in required if k not in envelope]
    if missing:
        raise RuntimeError(f"missing forecast envelope fields: {missing}")

    with tempfile.TemporaryDirectory(prefix="jnu_shadow_atomic_") as td:
        t=Path(td)
        di=t/"decision_input.json"
        trace=t/"decision_trace.json"
        draft=t/"forecast_draft.json"
        tmpout=t/"forecasts"
        di.write_text(json.dumps(decision_input,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        run([sys.executable,str(DECISION),"--input",str(di),"--output",str(trace)])
        decision_trace=json.loads(trace.read_text(encoding="utf-8"))
        forecast={
            **envelope,
            "bias":decision_trace["bias"],
            "confidence":decision_trace["confidence"],
            "decision_trace":decision_trace
        }
        draft.write_text(json.dumps(forecast,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        cp=run([sys.executable,str(REGISTRAR),"--input",str(draft),"--output-dir",str(tmpout)])
        info=json.loads(cp.stdout)
        src=Path(info["path"])
        fid=info["forecast_id"]
        args.output_dir.mkdir(parents=True,exist_ok=True)
        dst=args.output_dir/f"{fid}.json"
        if dst.exists():
            raise RuntimeError(f"forecast already exists in destination: {dst}")
        shutil.copy2(src,dst)

    commit_sha=None
    try:
        if real:
            rel=dst.relative_to(ROOT).as_posix()
            run(["git","add","--",rel])
            staged=run(["git","diff","--cached","--name-only"]).stdout.strip().splitlines()
            if staged!=[rel]:
                raise RuntimeError(f"unexpected staged files during forecast registration: {staged}")
            run(["git","commit","-m",f"Register JNU live-shadow forecast {fid}"])
            commit_sha=run(["git","rev-parse","HEAD"]).stdout.strip()
            run(["git","push","origin","main"])
            dirty=run(["git","status","--porcelain","--",rel]).stdout.strip()
            if dirty:
                raise RuntimeError(f"registered forecast is dirty after commit: {dirty}")
        print(json.dumps({
            "status":"FORECAST_REGISTERED_ATOMIC_COMMITTED" if real else "FORECAST_REGISTERED_ATOMIC_SELFTEST",
            "forecast_id":fid,
            "bias":forecast["bias"],
            "confidence":forecast["confidence"],
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
