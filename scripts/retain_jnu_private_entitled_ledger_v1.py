from __future__ import annotations
import argparse,json,os
from datetime import datetime,timezone,timedelta
from pathlib import Path
from jnu_private_atomic_io_v1 import backup_path,checksum_path,require_external
from jnu_private_lock_v1 import acquire_private_lock
from validate_jnu_private_launch_manifest_v1 import load as load_manifest,validate as validate_manifest
TAIPEI=timezone(timedelta(hours=8))
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--manifest",type=Path,required=True);ap.add_argument("--now-taipei");ap.add_argument("--apply",action="store_true");a=ap.parse_args()
    m=load_manifest(a.manifest);v=validate_manifest(m);root=Path(v["private_ledger_root"]);require_external(root,"private ledger root")
    if m["mode"]!="SYNTHETIC" or m["retention_policy_status"]!="SYNTHETIC_TEST_APPROVED":raise RuntimeError("retention apply is synthetic-only until license retention terms are confirmed")
    if m["permanent_purge_allowed"] is not False:raise RuntimeError("synthetic retention stage prohibits permanent purge")
    if a.apply and m["retention_quarantine_enabled"] is not True:raise RuntimeError("retention quarantine disabled")
    now=datetime.fromisoformat(a.now_taipei).astimezone(TAIPEI) if a.now_taipei else datetime.now(TAIPEI);cutoff=now.timestamp()-int(m["retention_days"])*86400
    with acquire_private_lock(root,"ledger-mutation",lease_seconds=300,wait_seconds=5,break_stale=False):
      fd=root/"forecasts";od=root/"outcomes";f={p.stem:p for p in fd.glob("*.json")} if fd.exists() else {};o={p.stem:p for p in od.glob("*.json")} if od.exists() else {}
        eligible=[]
      for fid in sorted(set(f)&set(o)):
          if max(f[fid].stat().st_mtime,o[fid].stat().st_mtime)<=cutoff:eligible.append(fid)
      moved=0
      if a.apply:
          q=root/"retention_quarantine"/"completed";q.mkdir(parents=True,exist_ok=True)
          for fid in eligible:
              pair=q/fid
              if pair.exists():raise RuntimeError("retention quarantine destination already exists")
              pair.mkdir(parents=True)
              for kind,p in [("forecast",f[fid]),("outcome",o[fid])]:
                  os.replace(p,pair/f"{kind}.json")
                  b=backup_path(root,p);s=checksum_path(b)
                  if b.exists():os.replace(b,pair/f"{kind}.backup.json")
                  if s.exists():os.replace(s,pair/f"{kind}.backup.json.sha256")
              moved+=1
    print(json.dumps({"status":"PASS","eligible_completed_pairs":len(eligible),"quarantined_pairs":moved,"pending_forecasts_skipped":len(set(f)-set(o)),"permanent_purge_performed":False},indent=2))
if __name__=="__main__":main()
