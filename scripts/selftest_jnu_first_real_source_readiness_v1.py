from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MODPATH=ROOT/"scripts"/"probe_jnu_first_real_source_readiness_v1.py"
spec=importlib.util.spec_from_file_location("probe_mod",MODPATH)
m=importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(m)

def write_script(path:Path, body:str)->None:
    path.write_text(body,encoding="utf-8")

def main()->None:
    tests={}
    with tempfile.TemporaryDirectory(prefix="jnu_source_probe_selftest_") as td0:
        td=Path(td0)
        fresh=td/"fresh.py"
        write_script(fresh, """import argparse,json
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--symbol'); p.add_argument('--max-age-seconds'); p.add_argument('--output',type=Path); a=p.parse_args()
q={'symbol':a.symbol,'price':65000.0,'source_timestamp':'2026-09-07T08:49:30+09:00','freshness_age_seconds':30.0,'freshness_pass':True,'exact_product':True,'continuous_contract':False}
a.output.write_text(json.dumps(q),encoding='utf-8')
""")
        stale=td/"stale.py"
        write_script(stale, """import sys
sys.stderr.write('RuntimeError: quote stale: age=901.0s > 900s; source=2026-09-07T08:34:00+09:00\\n')
raise SystemExit(1)
""")
        failure=td/"failure.py"
        write_script(failure, """import sys
sys.stderr.write('unexpected source schema failure\\n')
raise SystemExit(2)
""")
        unavailable=td/"unavailable.py"
        write_script(unavailable, """import sys
sys.stderr.write('RuntimeError: JPX exact Micro contract not found: Dec.2026\\n')
raise SystemExit(1)
""")
        bad_identity=td/"bad_identity.py"
        write_script(bad_identity, """import argparse,json
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--symbol'); p.add_argument('--max-age-seconds'); p.add_argument('--output',type=Path); a=p.parse_args()
q={'symbol':a.symbol,'price':65000.0,'source_timestamp':'2026-09-07T08:49:30+09:00','freshness_age_seconds':30.0,'freshness_pass':True,'exact_product':True,'continuous_contract':True}
a.output.write_text(json.dumps(q),encoding='utf-8')
""")

        r=m.classify("SYNTH_FRESH",fresh,"NK225MCU2026",900,td)
        tests["fresh_classified"]=r["status"]=="FRESH_PASS" and r["fresh"] is True and r["observed_age_seconds"]==30.0

        r=m.classify("SYNTH_STALE",stale,"NK225MCU2026",900,td)
        tests["stale_classified"]=r["status"]=="SOURCE_REACHABLE_STALE" and r["fresh"] is False and r["observed_age_seconds"]==901.0

        r=m.classify("SYNTH_FAILURE",failure,"NK225MCU2026",900,td)
        tests["failure_classified"]=r["status"]=="ENGINEERING_OR_SOURCE_FAILURE" and r["fresh"] is False

        r=m.classify("SYNTH_UNAVAILABLE",unavailable,"NK225MCZ2026",900,td)
        tests["contract_unavailable_classified"]=r["status"]=="CONTRACT_NOT_AVAILABLE_FROM_SOURCE" and r["fresh"] is False

        try:
            m.classify("SYNTH_BAD_IDENTITY",bad_identity,"NK225MCU2026",900,td)
            tests["continuous_identity_rejected"]=False
        except RuntimeError as exc:
            tests["continuous_identity_rejected"]="individual exact-Micro identity" in str(exc)

    status="PASS" if all(tests.values()) else "FAIL"
    print(json.dumps({"status":status,"tests":tests},ensure_ascii=False,indent=2))
    raise SystemExit(0 if status=="PASS" else 1)

if __name__=="__main__":
    main()
