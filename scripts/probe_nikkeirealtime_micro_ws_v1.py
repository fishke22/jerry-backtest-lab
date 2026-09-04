from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import websockets

WS_URL = "wss://con.nikkeirealtime.com/GIQS"
SYMBOL = "N225MC.FUT.OSE.CONT"


def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)


def source_dt(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x > 10_000_000_000:
        x /= 1000.0
    try:
        return datetime.fromtimestamp(x, timezone.utc)
    except Exception:
        return None


async def main():
    request = {
        "rk": "nrtquot",
        "wk": "qjnu_probe_1",
        "ty": "s",
        "sy": SYMBOL,
    }
    raws = []
    matches = []

    async with websockets.connect(
        WS_URL,
        origin="https://nikkeirealtime.com",
        user_agent_header="Mozilla/5.0 JNU-readonly-public-ws-probe/1.0",
        open_timeout=15,
        close_timeout=5,
        ping_interval=20,
        ping_timeout=10,
        max_size=2_000_000,
    ) as ws:
        await ws.send(json.dumps(request, separators=(",", ":")))
        deadline = asyncio.get_running_loop().time() + 15
        while asyncio.get_running_loop().time() < deadline and len(raws) < 100:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=3)
            except asyncio.TimeoutError:
                continue
            if isinstance(msg, bytes):
                msg = msg.decode("utf-8", "replace")
            raws.append(msg)
            try:
                obj = json.loads(msg)
            except Exception:
                continue
            for d in walk(obj):
                sy = d.get("sy")
                if sy == SYMBOL or (isinstance(sy, str) and SYMBOL in sy):
                    rec = dict(d)
                    tm = rec.get("tm")
                    dt = source_dt(tm)
                    if dt:
                        rec["_source_time_utc"] = dt.isoformat()
                        rec["_age_seconds_at_receive"] = (
                            datetime.now(timezone.utc) - dt
                        ).total_seconds()
                    matches.append(rec)
            if matches:
                # Keep listening briefly for a price-bearing update.
                if any(
                    any(k in m for k in ("la", "last", "price", "bi", "as"))
                    for m in matches
                ):
                    break

    Path("nikkeirealtime_ws_raw.jsonl").write_text(
        "\n".join(raws) + ("\n" if raws else ""),
        encoding="utf-8",
    )
    out = {
        "version": "1.0",
        "status": "WS_EXACT_MICRO_MATCH" if matches else "WS_NO_EXACT_MICRO_MATCH",
        "endpoint": WS_URL,
        "request": request,
        "raw_message_count": len(raws),
        "exact_symbol_match_count": len(matches),
        "matches": matches[:20],
        "received_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    Path("nikkeirealtime_ws_probe.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not matches:
        raise SystemExit(2)


if __name__ == "__main__":
    asyncio.run(main())
