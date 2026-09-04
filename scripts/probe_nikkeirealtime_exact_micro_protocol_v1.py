from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

PAGE = "https://nikkeirealtime.com/nikkei225-futures/"
KEYWORDS = [
    "GIQS",
    "N225MC.FUT.OSE.CONT",
    "N225MC",
    "nrtohlc",
    "WebSocket",
    "websocket",
    "wss://",
    "con.nikkeirealtime.com",
    "sourceTime",
    "sourceAt",
    "r.ut",
    "ut:",
    "nrtquot",
    "nrttick",
    "timestamp",
    "quote-time",
    "is-realtime",
]
UA = "Mozilla/5.0 JNU-public-protocol-probe/1.0"


def get(url: str) -> tuple[bytes, dict]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "*/*",
            "Referer": PAGE,
        },
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        data = r.read()
        headers = dict(r.headers.items())
        return data, headers


def snippets(text: str, needle: str, radius: int = 500) -> list[str]:
    out = []
    low = text.lower()
    nlow = needle.lower()
    start = 0
    while True:
        i = low.find(nlow, start)
        if i < 0:
            break
        a = max(0, i - radius)
        b = min(len(text), i + len(needle) + radius)
        out.append(text[a:b])
        start = i + max(1, len(needle))
        if len(out) >= 20:
            break
    return out


def main() -> None:
    page_bytes, page_headers = get(PAGE)
    page_text = page_bytes.decode("utf-8", "replace")
    srcs = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', page_text, re.I)
    urls = []
    for src in srcs:
        src = html.unescape(src)
        u = urllib.parse.urljoin(PAGE, src)
        if u not in urls:
            urls.append(u)

    result = {
        "version": "1.0",
        "status": "PROTOCOL_PROBE_COMPLETE",
        "page": PAGE,
        "page_sha256": hashlib.sha256(page_bytes).hexdigest(),
        "page_content_type": page_headers.get("Content-Type"),
        "script_count": len(urls),
        "scripts": [],
        "keyword_totals": {k: 0 for k in KEYWORDS},
    }

    raw_lines = []
    micro_tokens = set()
    for u in urls:
        try:
            data, headers = get(u)
            text = data.decode("utf-8", "replace")
            micro_tokens.update(re.findall(r"N225MC[A-Za-z0-9._:-]*", text))
            rec = {
                "url": u,
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
                "content_type": headers.get("Content-Type"),
                "hits": {},
            }
            for k in KEYWORDS:
                ss = snippets(text, k)
                if ss:
                    rec["hits"][k] = len(ss)
                    result["keyword_totals"][k] += len(ss)
                    for j, s in enumerate(ss, 1):
                        raw_lines.append(
                            f"\n=== URL {u}\n=== SHA256 {rec['sha256']}\n"
                            f"=== KEYWORD {k} MATCH {j}\n{s}\n"
                        )
            result["scripts"].append(rec)
        except Exception as e:
            result["scripts"].append({"url": u, "error": repr(e)})

    result["micro_contract_tokens"] = sorted(micro_tokens)

    Path("nikkeirealtime_protocol_probe.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path("nikkeirealtime_protocol_snippets.txt").write_text(
        "".join(raw_lines),
        encoding="utf-8",
    )
    print(json.dumps({
        "status": result["status"],
        "script_count": result["script_count"],
        "keyword_totals": result["keyword_totals"],
        "micro_contract_tokens": sorted(micro_tokens),
        "files_with_hits": [
            {"url": x["url"], "sha256": x.get("sha256"), "hits": x.get("hits")}
            for x in result["scripts"] if x.get("hits")
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
