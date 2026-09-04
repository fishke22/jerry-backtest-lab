from __future__ import annotations
import html, json, re, urllib.parse, urllib.request

BASE="https://nikkeirealtime.com"
PAGE=BASE+"/nikkei225-futures/"

def get(url:str)->str:
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 JNU-NRT-probe/3.0"})
    with urllib.request.urlopen(req,timeout=20) as r:
        return r.read().decode("utf-8","replace")

page=get(PAGE)
srcs=[]
for m in re.finditer(r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)["\']',page,re.I):
    u=urllib.parse.urljoin(PAGE,html.unescape(m.group(1)))
    if u.startswith(BASE+"/_next/"):
        srcs.append(u)
srcs=list(dict.fromkeys(srcs))
sources=[("PAGE_HTML",page)]
for u in srcs:
    try:
        sources.append((u,get(u)))
    except Exception:
        pass

def context_for(text:str, token:str, before:int=4500, after:int=9000):
    i=text.find(token)
    if i<0: return None
    return {"offset":i,"context":text[max(0,i-before):min(len(text),i+len(token)+after)]}

targets={}
for name,text in sources:
    # Exact module 8884 definition.
    for pat in ["8884:(", "8884:", "8884:function"]:
        c=context_for(text,pat)
        if c and "module_8884" not in targets:
            targets["module_8884"]={"source":name,"token":pat,**c}
    # WebSocket constructor and public endpoint.
    c=context_for(text,"wss://con.nikkeirealtime.com/GIQS",7000,12000)
    if c and "websocket_constructor" not in targets:
        targets["websocket_constructor"]={"source":name,**c}
    # Minified transport functions around the known subscription markers.
    for key,tok in [
        ("symbol_subscription",'rk:"$$symb"'),
        ("initial_snapshot",'nrtquot'),
        ("send_wrapper",'JSON.stringify'),
        ("push_decoder",'mt&&Array.isArray'),
        ("micro_registry",'N225MC.FUT.OSE.CONT'),
    ]:
        c=context_for(text,tok,6500,12000)
        if c and key not in targets:
            targets[key]={"source":name,"token":tok,**c}

# Also use regex to find minified ac/aC/av declarations in the same source as the websocket.
ws_source=targets.get("websocket_constructor",{}).get("source")
if ws_source:
    text=dict(sources)[ws_source]
    for key,pat in [
        ("ac_declaration",r'(?<![A-Za-z0-9_$])ac\s*='),
        ("aC_declaration",r'(?<![A-Za-z0-9_$])aC\s*='),
        ("av_declaration",r'(?<![A-Za-z0-9_$])av\s*='),
    ]:
        m=re.search(pat,text)
        if m:
            i=m.start()
            targets[key]={"source":ws_source,"offset":i,"context":text[max(0,i-5000):min(len(text),i+12000)]}

summary={
  "status":"NRT_PROTOCOL_SURGICAL_PROBE",
  "script_count":len(srcs),
  "target_keys":sorted(targets),
  "targets":targets,
}
print(json.dumps(summary,ensure_ascii=False,indent=2))

required=["websocket_constructor","symbol_subscription","initial_snapshot","micro_registry"]
missing=[x for x in required if x not in targets]
if missing:
    raise RuntimeError(f"required protocol contexts missing: {missing}")
