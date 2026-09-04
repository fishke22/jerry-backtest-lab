from __future__ import annotations

import asyncio
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import websockets

TV_URL="https://quotes.tradingview.com/quote_cache_http/snapshot"
TV_SYMBOL="OSE:NK225MCU2026"
NR_WS="wss://con.nikkeirealtime.com/GIQS"
NR_SYMBOL="N225MC.FUT.OSE.CONT"


def tv_anchor():
    fields="lp,lp_time,exchange,source_id,original_name,description,root,type,currency_code,update_mode,contract-date,expiration"
    url=TV_URL+"?"+urllib.parse.urlencode({"fields":fields})
    req=urllib.request.Request(
        url,data=json.dumps([TV_SYMBOL]).encode(),method="POST",
        headers={"Origin":"https://www.tradingview.com","Referer":"https://www.tradingview.com/",
                 "Content-Type":"application/json","User-Agent":"Mozilla/5.0 JNU-nrttick-probe/1.0",
                 "Cookie":"sessionid=; sessionid_sign="})
    with urllib.request.urlopen(req,timeout=20) as r:
        x=json.loads(r.read().decode("utf-8","replace"))
    d=x[0]["data"]
    return {"price":float(d["lp"]),"time":int(float(d["lp_time"])),"data":d}


def walk(x,path=()):
    yield path,x
    if isinstance(x,dict):
        for k,v in x.items():
            yield from walk(v,path+(str(k),))
    elif isinstance(x,list):
        for i,v in enumerate(x):
            yield from walk(v,path+(str(i),))


async def get_tick():
    req={"rk":"nrttick","wk":"jnu_tick_crossmap","sy":NR_SYMBOL,"ft":"t","ty":"t","iv":"300","rn":"288"}
    raws=[]
    objs=[]
    async with websockets.connect(
        NR_WS,origin="https://nikkeirealtime.com",
        user_agent_header="Mozilla/5.0 JNU-nrttick-probe/1.0",
        open_timeout=15,close_timeout=5,ping_interval=20,max_size=8_000_000
    ) as ws:
        await ws.send(json.dumps(req,separators=(",",":")))
        deadline=asyncio.get_running_loop().time()+10
        while asyncio.get_running_loop().time()<deadline and len(raws)<20:
            try:
                msg=await asyncio.wait_for(ws.recv(),timeout=2)
            except asyncio.TimeoutError:
                continue
            if isinstance(msg,bytes): msg=msg.decode("utf-8","replace")
            raws.append(msg)
            try: obj=json.loads(msg)
            except Exception: continue
            objs.append(obj)
            if isinstance(obj,dict) and (obj.get("wk")==req["wk"] or obj.get("rk")=="nrttick"):
                break
    return req,raws,objs


async def main():
    tv=tv_anchor()
    req,raws,objs=await get_tick()
    anchor=tv["time"]; price=tv["price"]

    exact_timestamp_paths=[]
    exact_price_paths=[]
    paired_candidates=[]
    for oi,obj in enumerate(objs):
        for path,val in walk(obj):
            if isinstance(val,(int,float)):
                if int(val)==anchor:
                    exact_timestamp_paths.append({"object":oi,"path":path,"value":val})
                if float(val)==price:
                    exact_price_paths.append({"object":oi,"path":path,"value":val})
            if isinstance(val,list) and 2<=len(val)<=12:
                nums=[v for v in val if isinstance(v,(int,float))]
                if anchor in nums or price in [float(v) for v in nums]:
                    paired_candidates.append({"object":oi,"path":path,"value":val})

    exact_pair=False
    for c in paired_candidates:
        vals=c["value"]
        if any(isinstance(v,(int,float)) and int(v)==anchor for v in vals) and any(isinstance(v,(int,float)) and float(v)==price for v in vals):
            exact_pair=True

    out={
      "version":"1.0",
      "status":"NRTTICK_EXACT_PAIR_PASS" if exact_pair else "NRTTICK_EXACT_PAIR_NOT_FOUND",
      "tradingview_anchor":{
        "symbol":TV_SYMBOL,"price":price,"lp_time":anchor,
        "lp_time_utc":datetime.fromtimestamp(anchor,timezone.utc).isoformat(),
        "original_name":tv["data"].get("original_name"),
        "contract_date":tv["data"].get("contract-date"),
        "expiration":tv["data"].get("expiration"),
        "update_mode":tv["data"].get("update_mode"),
      },
      "nikkeirealtime":{"symbol":NR_SYMBOL,"endpoint":NR_WS,"request":req,
                         "raw_message_count":len(raws),"objects":objs},
      "exact_timestamp_paths":exact_timestamp_paths[:100],
      "exact_price_paths":exact_price_paths[:100],
      "paired_candidates":paired_candidates[:100],
      "exact_timestamp_price_pair_found":exact_pair,
      "checked_at_utc":datetime.now(timezone.utc).isoformat(),
    }
    Path("jnu_nrttick_crossmap_probe.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    Path("jnu_nrttick_raw.jsonl").write_text("\n".join(raws)+("\n" if raws else ""),encoding="utf-8")
    print(json.dumps({k:v for k,v in out.items() if k!="nikkeirealtime"} | {
        "nrttick_request":req,"nrttick_raw_message_count":len(raws),
        "nrttick_objects":objs
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    asyncio.run(main())
