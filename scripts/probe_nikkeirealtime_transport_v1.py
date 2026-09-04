from __future__ import annotations
import html, json, re, urllib.parse, urllib.request

BASE="https://nikkeirealtime.com"
PAGE=BASE+"/nikkei225-futures/"
TOKENS=[
    "N225MC.FUT.OSE.CONT",
    "wss://con.nikkeirealtime.com/GIQS",
    "sourceAt",
    "lastTickAt",
    "feedSymbol",
    "sourceType",
    "8884:",
    "function ac",
    "ac=",
    "aC=",
    "av=",
    'rk:"$$symb"',
    "nrtquot",
    "JSON.stringify",
    ".send(",
]
def get(url:str)->str:
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 JNU-NRT-probe/2.0"})
    with urllib.request.urlopen(req,timeout=20) as r:
        return r.read().decode("utf-8","replace")

page=get(PAGE)
srcs=[]
for m in re.finditer(r'<script[^>]+src=["\']([^"\']+\.js[^"\']*)["\']',page,re.I):
    u=urllib.parse.urljoin(PAGE,html.unescape(m.group(1)))
    if u.startswith(BASE+"/_next/"):
        srcs.append(u)
srcs=list(dict.fromkeys(srcs))
print(json.dumps({"status":"PAGE_FETCHED","script_count":len(srcs),"scripts":srcs},ensure_ascii=False,indent=2))

sources=[("PAGE_HTML",page)]
for u in srcs:
    try:
        sources.append((u,get(u)))
    except Exception as e:
        print(json.dumps({"warning":"SCRIPT_FETCH_FAILED","url":u,"error":repr(e)},ensure_ascii=False))

matches=[]
for name,text in sources:
    for token in TOKENS:
        start=0
        found=0
        while found<6:
            i=text.find(token,start)
            if i<0: break
            found+=1
            lo=max(0,i-3200); hi=min(len(text),i+len(token)+7200)
            matches.append({
                "source":name,
                "token":token,
                "occurrence":found,
                "offset":i,
                "context":text[lo:hi],
            })
            start=i+len(token)

# Compact index first, full contexts after it.
print(json.dumps({
    "status":"TOKEN_INDEX",
    "matches":[{"source":m["source"],"token":m["token"],"occurrence":m["occurrence"],"offset":m["offset"]} for m in matches]
},ensure_ascii=False,indent=2))
print(json.dumps({"status":"RAW_TOKEN_CONTEXTS","match_count":len(matches),"matches":matches},ensure_ascii=False,indent=2))

required=["N225MC.FUT.OSE.CONT","wss://con.nikkeirealtime.com/GIQS",'rk:"$$symb"',"nrtquot"]
missing=[t for t in required if not any(m["token"]==t for m in matches)]
if missing:
    raise RuntimeError(f"required transport tokens not found: {missing}")
