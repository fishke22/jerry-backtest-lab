from __future__ import annotations

import asyncio
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import websockets

TV_URL = "https://quotes.tradingview.com/quote_cache_http/snapshot"
TV_SYMBOL = "OSE:NK225MCU2026"
NR_WS = "wss://con.nikkeirealtime.com/GIQS"
NR_SYMBOL = "N225MC.FUT.OSE.CONT"


def tv_quote() -> dict:
    fields = ",".join([
        "lp","lp_time","exchange","source_id","original_name","description",
        "root","type","currency_code","update_mode","contract-date","expiration"
    ])
    url = TV_URL + "?" + urllib.parse.urlencode({"fields": fields})
    req = urllib.request.Request(
        url,
        data=json.dumps([TV_SYMBOL]).encode(),
        method="POST",
        headers={
            "Origin":"https://www.tradingview.com",
            "Referer":"https://www.tradingview.com/",
            "Content-Type":"application/json",
            "User-Agent":"Mozilla/5.0 JNU-crossmap-probe/1.0",
            "Cookie":"sessionid=; sessionid_sign=",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        x=json.loads(r.read().decode("utf-8","replace"))
    if not isinstance(x,list) or len(x)!=1 or x[0].get("s")!="ok":
        raise RuntimeError("TradingView quote-cache response invalid")
    d=x[0]["data"]
    if x[0].get("symbol")!=TV_SYMBOL:
        raise RuntimeError("TradingView symbol mismatch")
    if d.get("exchange")!="OSE" or d.get("source_id")!="OSE":
        raise RuntimeError("TradingView OSE identity mismatch")
    if d.get("root")!="NK225MC" or d.get("type")!="futures":
        raise RuntimeError("TradingView Micro identity mismatch")
    return d


def parse_bars(obj) -> list[list]:
    bars=[]
    def walk(x):
        if isinstance(x,dict):
            ca=x.get("ca")
            if isinstance(ca,list):
                for row in ca:
                    if isinstance(row,list) and len(row)>=5:
                        bars.append(row)
            for v in x.values():
                walk(v)
        elif isinstance(x,list):
            for v in x:
                walk(v)
    walk(obj)
    # unique by full row serialization
    out=[]; seen=set()
    for row in bars:
        k=json.dumps(row,separators=(",",":"),ensure_ascii=False)
        if k not in seen:
            seen.add(k); out.append(row)
    return out


async def nr_ohlc(anchor:int, request_type:str) -> dict:
    req={
        "rk":"nrtohlc",
        "wk":f"jnu_map_{request_type}",
        "sy":NR_SYMBOL,
        "ut":str(anchor),
        "ft":"t",
        "ty":request_type,
        "iv":"60",
        "rn":"10",
    }
    raws=[]
    async with websockets.connect(
        NR_WS,
        origin="https://nikkeirealtime.com",
        user_agent_header="Mozilla/5.0 JNU-crossmap-probe/1.0",
        open_timeout=15,
        close_timeout=5,
        ping_interval=20,
        max_size=2_000_000,
    ) as ws:
        await ws.send(json.dumps(req,separators=(",",":")))
        deadline=asyncio.get_running_loop().time()+8
        while asyncio.get_running_loop().time()<deadline and len(raws)<30:
            try:
                msg=await asyncio.wait_for(ws.recv(),timeout=2)
            except asyncio.TimeoutError:
                continue
            if isinstance(msg,bytes):
                msg=msg.decode("utf-8","replace")
            raws.append(msg)
            try:
                obj=json.loads(msg)
            except Exception:
                continue
            if isinstance(obj,dict):
                if obj.get("wk")==req["wk"] or obj.get("rk")=="nrtohlc" or isinstance(obj.get("ca"),list):
                    return {"request":req,"response":obj,"raws":raws}
        return {"request":req,"response":None,"raws":raws}


async def main():
    tv=tv_quote()
    anchor=int(float(tv["lp_time"]))
    tv_price=float(tv["lp"])
    attempts=[]
    selected=None
    for ty in ("t","c","b"):
        x=await nr_ohlc(anchor,ty)
        bars=parse_bars(x.get("response"))
        rec={
            "request":x["request"],
            "response":x["response"],
            "raw_message_count":len(x["raws"]),
            "bars":bars,
        }
        attempts.append(rec)
        if bars:
            selected=rec
            break

    matches=[]
    if selected:
        for row in selected["bars"]:
            try:
                ts=int(float(row[0])); close=float(row[4])
            except Exception:
                continue
            if ts==anchor:
                matches.append({
                    "timestamp":ts,
                    "close":close,
                    "price_equal":close==tv_price,
                })

    status="CROSSMAP_EXACT_PASS" if matches and any(x["price_equal"] for x in matches) else "CROSSMAP_NOT_PROVEN"
    out={
        "version":"1.0",
        "status":status,
        "tradingview":{
            "symbol":TV_SYMBOL,
            "price":tv_price,
            "lp_time":anchor,
            "lp_time_utc":datetime.fromtimestamp(anchor,timezone.utc).isoformat(),
            "original_name":tv.get("original_name"),
            "contract_date":tv.get("contract-date"),
            "expiration":tv.get("expiration"),
            "update_mode":tv.get("update_mode"),
        },
        "nikkeirealtime":{
            "symbol":NR_SYMBOL,
            "endpoint":NR_WS,
            "attempts":attempts,
        },
        "same_timestamp_matches":matches,
        "checked_at_utc":datetime.now(timezone.utc).isoformat(),
    }
    Path("jnu_micro_crossmap_probe.json").write_text(
        json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
    )
    print(json.dumps(out,ensure_ascii=False,indent=2))
    if status!="CROSSMAP_EXACT_PASS":
        raise SystemExit(3)


if __name__=="__main__":
    asyncio.run(main())
