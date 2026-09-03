from __future__ import annotations
import argparse, json, re, shutil, subprocess, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

TAIPEI=timezone(timedelta(hours=8))
SYMBOL_RE=re.compile(r"^NK225MC[A-Z][0-9]{4}$")
NUM_RE=re.compile(r"^[+−-]?[0-9][0-9,]*(?:\.[0-9]+)?%?$")

def agent_command()->list[str]:
    node=shutil.which("node")
    npm=shutil.which("npm.cmd") or shutil.which("npm")
    if not node or not npm:
        raise RuntimeError("node/npm not found")
    root=subprocess.run([npm,"root","-g"],check=True,capture_output=True,text=True,encoding="utf-8",errors="replace").stdout.strip()
    js=Path(root)/"agent-browser"/"bin"/"agent-browser.js"
    if not js.exists():
        raise RuntimeError(f"agent-browser JS not found: {js}")
    return [node,str(js)]

def run_agent(args:list[str],timeout:int=20)->str:
    cp=subprocess.run([*agent_command(),*args],check=True,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=timeout)
    return cp.stdout.strip()

def decode_eval_json(stdout:str):
    x=json.loads(stdout)
    if isinstance(x,str):
        return json.loads(x)
    return x

def open_symbol(symbol:str,session:str,reuse_session:bool=False)->None:
    url=f"https://www.tradingview.com/symbols/OSE-{symbol}/"
    if reuse_session:
        try:
            current=run_agent(["--session",session,"get","url"],timeout=8).strip()
            if current.rstrip("/").lower()==url.rstrip("/").lower():
                return
        except Exception:
            pass
    run_agent(["--session",session,"open",url])
    run_agent(["--session",session,"wait","450"])

def body_identity(symbol:str,session:str)->dict:
    body=run_agent(["--session",session,"get","text","body"])
    lines=[x.strip() for x in body.splitlines() if x.strip()]
    occ=[i for i,x in enumerate(lines) if x==symbol]
    if not occ:
        raise RuntimeError(f"symbol {symbol} not found in TradingView page")
    first=occ[0]
    window=lines[max(0,(occ[1] if len(occ)>1 else first)-8):(occ[1] if len(occ)>1 else first)+20]
    if "Osaka Exchange" not in window:
        raise RuntimeError("Osaka Exchange identity not found near symbol")
    if not any("Nikkei 225 micro Futures" in x for x in window):
        raise RuntimeError("Nikkei 225 micro Futures identity not found near symbol")
    price_text=lines[first+1]
    currency=lines[first+3]
    change_text=lines[first+4]
    change_pct_text=lines[first+5]
    if currency!="JPY":
        raise RuntimeError(f"unexpected currency: {currency}")
    if not NUM_RE.match(price_text) or not NUM_RE.match(change_text) or not NUM_RE.match(change_pct_text):
        raise RuntimeError("unexpected quote header fields")
    state=next((x for x in lines if x in {"Market open","Market closed","No trades"}),None)
    contract_name=next((x for x in window if "contract" in x.lower() and x!="Continuous contract"),None)
    return {
      "displayed_price":float(price_text.replace(",","")),
      "displayed_change":float(change_text.replace(",","").replace("−","-")),
      "displayed_change_pct":float(change_pct_text.replace("%","").replace("−","-")),
      "market_state":state,
      "contract_name":contract_name
    }


def atomic_page_state(symbol:str,session:str)->dict:
    expr=(
      "(()=>{try{const q=window.getQuoteSessionInstance();"
      f"const z=(q._symbol_data['OSE:{symbol}']||{{}}).values||{{}};"
      "const lines=(document.body.innerText||'').split(String.fromCharCode(10)).map(x=>x.replace(String.fromCharCode(13),'').trim()).filter(Boolean).slice(0,80);"
      "return JSON.stringify({url:location.href,lines,z:{last_price:z.last_price,lp_time:z.lp_time,bid:z.bid,ask:z.ask,"
      "update_mode:z.update_mode,update_mode_seconds:z.update_mode_seconds,source_id:z.source_id,"
      "provider_id:z.provider_id,original_name:z.original_name,description:z.description,type:z.type,"
      "timezone:z.timezone,currency_code:z.currency_code,root:z.root,expiration:z.expiration,"
      "contract_date:z['contract-date'],subsession_id:z.subsession_id,rt_update_period:z.rt_update_period}});"
      "}catch(e){return JSON.stringify({error:e.message})}})()"
    )
    out=decode_eval_json(run_agent(["--session",session,"eval",expr]))
    if out.get("error"):
        raise RuntimeError(f"TradingView atomic snapshot error: {out['error']}")
    return out

def quote_state(symbol:str,session:str)->dict:
    expr=(
      "(()=>{try{const q=window.getQuoteSessionInstance();"
      f"const z=(q._symbol_data['OSE:{symbol}']||{{}}).values||{{}};"
      "return JSON.stringify({last_price:z.last_price,lp_time:z.lp_time,bid:z.bid,ask:z.ask,"
      "update_mode:z.update_mode,update_mode_seconds:z.update_mode_seconds,source_id:z.source_id,"
      "provider_id:z.provider_id,original_name:z.original_name,description:z.description,type:z.type,"
      "timezone:z.timezone,currency_code:z.currency_code,root:z.root,expiration:z.expiration,"
      "contract_date:z['contract-date'],subsession_id:z.subsession_id,rt_update_period:z.rt_update_period});"
      "}catch(e){return JSON.stringify({error:e.message})}})()"
    )
    out=decode_eval_json(run_agent(["--session",session,"eval",expr]))
    if out.get("error"):
        raise RuntimeError(f"TradingView quote-session error: {out['error']}")
    required=["last_price","lp_time","update_mode","source_id","description","type","currency_code"]
    missing=[k for k in required if out.get(k) is None]
    if missing:
        raise RuntimeError(f"TradingView quote-session fields missing: {missing}")
    if out["source_id"]!="OSE":
        raise RuntimeError(f"unexpected source_id: {out['source_id']}")
    if out["type"]!="futures" or "micro" not in str(out["description"]).lower():
        raise RuntimeError("quote-session does not identify Nikkei 225 Micro futures")
    if out["currency_code"]!="JPY":
        raise RuntimeError("unexpected quote-session currency")
    return out

def fetch_once(symbol:str,session:str,max_age:int,reuse_session:bool=False)->dict:
    open_symbol(symbol,session,reuse_session=reuse_session)
    snap=atomic_page_state(symbol,session)
    z=snap.get("z") or {}
    required=["last_price","lp_time","update_mode","source_id","description","type","currency_code"]
    missing=[k for k in required if z.get(k) is None]
    if missing:
        raise RuntimeError(f"TradingView atomic snapshot fields missing: {missing}")
    if z.get("source_id")!="OSE" or z.get("type")!="futures" or "micro" not in str(z.get("description","")).lower() or z.get("currency_code")!="JPY":
        raise RuntimeError("TradingView atomic snapshot product/source identity invalid")
    lines=snap.get("lines") or []
    if symbol not in lines or "Osaka Exchange" not in lines or not any("Nikkei 225 micro Futures" in x for x in lines):
        raise RuntimeError("TradingView DOM identity invalid")
    occ=[i for i,x in enumerate(lines) if x==symbol]
    first=occ[0]
    price_text=lines[first+1] if first+1<len(lines) else ""
    displayed_price=float(price_text.replace(",","")) if NUM_RE.match(price_text) else None
    market_state=next((x for x in lines if x in {"Market open","Market closed","No trades"}),None)
    contract_name=next((x for x in lines if "contract" in x.lower() and x!="Continuous contract"),None)
    change=None; change_pct=None
    if first+5<len(lines):
        try: change=float(lines[first+4].replace(",","").replace("−","-"))
        except: pass
        try: change_pct=float(lines[first+5].replace("%","").replace("−","-"))
        except: pass
    now=datetime.now(TAIPEI)
    source_at=datetime.fromtimestamp(float(z["lp_time"]),timezone.utc).astimezone(TAIPEI)
    age=(now-source_at).total_seconds()
    return {
      "version":"1.2",
      "provider":"TradingView public symbol page",
      "data_provider_id":z.get("provider_id"),
      "source_id":z.get("source_id"),
      "source_original_name":z.get("original_name"),
      "symbol":symbol,
      "tradingview_symbol":f"OSE:{symbol}",
      "contract_name":contract_name,
      "contract_date":z.get("contract_date"),
      "expiration_epoch":z.get("expiration"),
      "exchange":"Osaka Exchange",
      "product":"Nikkei 225 micro Futures",
      "price":float(z["last_price"]),
      "displayed_price_same_atomic_snapshot":displayed_price,
      "dom_quote_price_equal":displayed_price is not None and abs(float(z["last_price"])-displayed_price)<=1e-9,
      "bid":z.get("bid"),
      "ask":z.get("ask"),
      "currency":"JPY",
      "change":change,
      "change_pct":change_pct,
      "market_state":market_state,
      "source_timestamp_epoch":int(z["lp_time"]),
      "source_timestamp":source_at.isoformat(),
      "freshness_checked_at":now.isoformat(),
      "freshness_age_seconds":age,
      "maximum_allowed_age_seconds":max_age,
      "freshness_pass":0<=age<=max_age,
      "exact_product":True,
      "continuous_contract":False,
      "update_mode":z.get("update_mode"),
      "declared_update_mode_seconds":z.get("update_mode_seconds"),
      "rt_update_period":z.get("rt_update_period"),
      "subsession_id":z.get("subsession_id"),
      "url":f"https://www.tradingview.com/symbols/OSE-{symbol}/",
      "delayed_data":str(z.get("update_mode","")).startswith("delayed"),
      "adapter_mode":"warm_session_reuse" if reuse_session else "open_and_validate"
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--symbol",required=True)
    ap.add_argument("--session",default="jnu_exact_micro")
    ap.add_argument("--max-age-seconds",type=int,default=900)
    ap.add_argument("--max-wait-seconds",type=int,default=0)
    ap.add_argument("--poll-seconds",type=int,default=5)
    ap.add_argument("--output",type=Path)
    ap.add_argument("--reuse-session",action="store_true",help="Reuse the existing exact-symbol browser session when already on the same URL; does not change source or freshness rules.")
    args=ap.parse_args()
    symbol=args.symbol.upper()
    if not SYMBOL_RE.match(symbol):
        raise RuntimeError("symbol must be an individual OSE Nikkei 225 Micro contract such as NK225MCU2026")
    deadline=time.monotonic()+max(0,args.max_wait_seconds)
    while True:
        q=fetch_once(symbol,args.session,args.max_age_seconds,reuse_session=args.reuse_session)
        if q["freshness_pass"]:
            break
        if args.max_wait_seconds<=0 or time.monotonic()>=deadline:
            raise RuntimeError(f"quote stale: age={q['freshness_age_seconds']:.1f}s > {args.max_age_seconds}s; source={q['source_timestamp']}")
        time.sleep(max(1,args.poll_seconds))
    s=json.dumps(q,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(s+"\n",encoding="utf-8")
    print(s)

if __name__=="__main__":
    main()
