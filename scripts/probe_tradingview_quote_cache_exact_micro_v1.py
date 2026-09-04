from __future__ import annotations
import json, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

SYMBOL="OSE:NK225MCU2026"
FIELDS=[
  "current_session","type","update_mode","update_mode_seconds","original_name",
  "short_name","pro_name","description","local_description","exchange","source_id",
  "currency_code","root","expiration","contract-date","symbol_status","lp","ch","chp",
  "lp_time","bid","ask","rtc","rch","rchp"
]
url="https://quotes.tradingview.com/quote_cache_http/snapshot?"+urllib.parse.urlencode({"fields":",".join(FIELDS)})
body=json.dumps([SYMBOL]).encode("utf-8")
req=urllib.request.Request(
    url,
    data=body,
    method="POST",
    headers={
      "Origin":"https://www.tradingview.com",
      "Referer":"https://www.tradingview.com/",
      "Content-Type":"application/json",
      "User-Agent":"Mozilla/5.0 JNU-quote-cache-probe/1.0",
      "Cookie":"sessionid=; sessionid_sign="
    }
)
try:
    with urllib.request.urlopen(req,timeout=20) as r:
        raw=r.read().decode("utf-8","replace")
        status=r.status
        headers=dict(r.headers.items())
except Exception as e:
    print(json.dumps({"status":"HTTP_PROBE_ERROR","error":repr(e)},indent=2))
    raise
print(json.dumps({"http_status":status,"response_headers":{k:v for k,v in headers.items() if k.lower() in {"content-type","cache-control","date"}}},indent=2))
print(raw)
x=json.loads(raw)
if not isinstance(x,list) or len(x)!=1:
    raise RuntimeError(f"unexpected response shape: {type(x).__name__} len={len(x) if isinstance(x,list) else 'n/a'}")
item=x[0]
print(json.dumps({"item_keys":sorted(item.keys()),"item":item},ensure_ascii=False,indent=2))
sym=item.get("symbol") or item.get("s")
data=item.get("data") if isinstance(item.get("data"),dict) else item.get("d")
if sym!=SYMBOL:
    raise RuntimeError(f"symbol mismatch: {sym!r}")
if not isinstance(data,dict):
    raise RuntimeError("quote data object missing")
required=["lp","lp_time","update_mode","type","description"]
missing=[k for k in required if data.get(k) is None]
if missing:
    raise RuntimeError(f"required fields missing: {missing}")
ts=datetime.fromtimestamp(float(data["lp_time"]),timezone.utc)
print(json.dumps({
  "status":"QUOTE_CACHE_EXACT_MICRO_PROBE_PASS",
  "symbol":sym,
  "price":data["lp"],
  "lp_time":data["lp_time"],
  "lp_time_utc":ts.isoformat(),
  "update_mode":data.get("update_mode"),
  "exchange":data.get("exchange"),
  "source_id":data.get("source_id"),
  "original_name":data.get("original_name"),
  "pro_name":data.get("pro_name"),
  "description":data.get("description"),
  "type":data.get("type"),
  "currency_code":data.get("currency_code"),
  "root":data.get("root")
},ensure_ascii=False,indent=2))
