from __future__ import annotations
import argparse, json, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

TAIPEI=timezone(timedelta(hours=8))
JST=timezone(timedelta(hours=9))
URL="https://port.jpx.co.jp/jpxhp/jcgi/wrap/qjsonp.aspx?F=ctl/future&DISPTYPE=day_through"
PRODUCT_JA="日経225マイクロ先物"
PRODUCT_EN="Nikkei 225 micro Futures"
MONTH_CODES={"F":"Jan","G":"Feb","H":"Mar","J":"Apr","K":"May","M":"Jun","N":"Jul","Q":"Aug","U":"Sep","V":"Oct","X":"Nov","Z":"Dec"}

def month_label_from_symbol(symbol:str)->str:\n    s=symbol.upper()\n    if len(s)!=12 or not s.startswith("NK225MC") or s[7] not in MONTH_CODES or not s[8:].isdigit():\n        raise RuntimeError("symbol must be an individual OSE Nikkei 225 Micro contract such as NK225MCU2026")\n    return f"{MONTH_CODES[s[7]]}.{s[8:]}"\n
def parse_mmdd_hhmm(mmdd:str, hhmm:str, now:datetime)->datetime:
    month,day=map(int,mmdd.split('/'))
    now_jst=now.astimezone(JST)
    dt=datetime(now_jst.year,month,day,int(hhmm[:2]),int(hhmm[3:]),0,tzinfo=JST)
    if dt>now_jst+timedelta(days=30):
        dt=dt.replace(year=dt.year-1)
    return dt

def num(s:str)->float:
    return float(str(s).replace(',',''))

def integer(s:str)->int:
    return int(str(s).replace(',',''))

def fetch_payload()->dict:
    r=requests.get(URL,timeout=10,headers={'User-Agent':'Mozilla/5.0 JNU-research-readonly/1.0'})
    r.raise_for_status()
    x=r.json()
    if not isinstance(x,dict) or 'section1' not in x:
        raise RuntimeError('unexpected JPX futures payload')
    return x

def select_contract(payload:dict, month_label:str)->tuple[dict,dict]:
    groups=payload.get('section1',{}).get('data',[])
    group=next((g for g in groups if g.get('name')==PRODUCT_JA),None)
    if group is None:
        raise RuntimeError('JPX Micro product group not found')
    contract=next((f for f in group.get('future',[]) if f.get('DELIE')==month_label),None)
    if contract is None:
        raise RuntimeError(f'JPX exact Micro contract not found: {month_label}')
    return group,contract

def fetch_once(month_label:str,max_age:int)->dict:
    payload=fetch_payload()
    group,c=select_contract(payload,month_label)
    now=datetime.now(TAIPEI)
    if c.get('DPP') in {None,'-'} or c.get('DPPT') in {None,'-'}:
        raise RuntimeError('JPX Last field is unavailable')
    last_ts=parse_mmdd_hhmm(c['DPP_H'],c['DPPT'],now)
    age=(now-last_ts.astimezone(TAIPEI)).total_seconds()
    ask_ts=parse_mmdd_hhmm(c['DPP_H'],c['QAPT'],now) if c.get('QAPT') not in {None,'-'} else None
    bid_ts=parse_mmdd_hhmm(c['DPP_H'],c['QBPT'],now) if c.get('QBPT') not in {None,'-'} else None
    return {
      'version':'1.1','provider':'Japan Exchange Group / Osaka Exchange',
      'endpoint':URL,'source_quality':'A','source_id':'JPX_OSE_OFFICIAL',
      'product':PRODUCT_EN,'product_group_qcode':group.get('qcode'),
      'contract_month':month_label,'contract_code':c.get('TTCODE'),
      'contract_code_short':c.get('TTCODE2'),'trading_date':c.get('ZTD'),
      'price':num(c['DPP']),'currency':'JPY',
      'source_timestamp_jst':last_ts.isoformat(),
      'source_timestamp':last_ts.astimezone(TAIPEI).isoformat(),
      'change':num(c['DYWP']),'volume':integer(c['DV']),
      'ask':None if c.get('QAP') in {None,'-'} else num(c['QAP']),
      'ask_timestamp_jst':None if ask_ts is None else ask_ts.isoformat(),
      'bid':None if c.get('QBP') in {None,'-'} else num(c['QBP']),
      'bid_timestamp_jst':None if bid_ts is None else bid_ts.isoformat(),
      'open':None if c.get('DOP') in {None,'-'} else num(c['DOP']),
      'high':None if c.get('DHP') in {None,'-'} else num(c['DHP']),
      'low':None if c.get('DLP') in {None,'-'} else num(c['DLP']),
      'open_interest':None if c.get('DOI') in {None,'-'} else integer(c['DOI']),
      'freshness_checked_at':now.isoformat(),'freshness_age_seconds':age,
      'maximum_allowed_age_seconds':max_age,'freshness_pass':0<=age<=max_age,
      'timestamp_precision':'minute','timestamp_conservative_second':0,
      'exact_product':True,'continuous_contract':False,
      'official_exchange_source':True,'last_field_only_primary_reference':True,
      'public_quote_delay_disclosure':'JPX public quotes may be delayed; freshness gate is never waived.'
    }

def main():
    ap=argparse.ArgumentParser()
    g=ap.add_mutually_exclusive_group(required=True)\n    g.add_argument('--month',help='JPX month label, e.g. Sep.2026')\n    g.add_argument('--symbol',help='Individual OSE Micro symbol, e.g. NK225MCU2026')
    ap.add_argument('--max-age-seconds',type=int,default=900)
    ap.add_argument('--max-wait-seconds',type=int,default=0)
    ap.add_argument('--poll-seconds',type=int,default=5)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    month_label=args.month or month_label_from_symbol(args.symbol)\n    deadline=time.monotonic()+max(0,args.max_wait_seconds)\n    while True:\n        q=fetch_once(month_label,args.max_age_seconds)\n        if args.symbol:\n            q["symbol"]=args.symbol.upper()
        if q['freshness_pass']:
            break
        if args.max_wait_seconds<=0 or time.monotonic()>=deadline:
            raise RuntimeError(f"JPX quote stale: age={q['freshness_age_seconds']:.1f}s > {args.max_age_seconds}s; source={q['source_timestamp_jst']}")
        time.sleep(max(1,args.poll_seconds))
    s=json.dumps(q,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(s+'\n',encoding='utf-8')
    print(s)

if __name__=='__main__':
    main()
