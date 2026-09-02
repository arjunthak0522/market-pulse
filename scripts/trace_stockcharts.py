#!/usr/bin/env python3
"""Audit StockCharts QuoteBrain support for every Market Pulse current signal input."""
import json
import time
import requests

UA={"User-Agent":"Mozilla/5.0 MarketPulse/1.0","Accept":"application/json,text/plain,*/*"}
SYMBOLS=[
    "$CPCE",
    "$NYADV","$NYDEC","$NYUPV","$NYDNV","$NYHGH","$NYLOW","$NYTOT","$NYMO","$TRIN",
    "$NAADV","$NADEC","$NAUPV","$NADNV","$NAHGH","$NALOW","$NATOT","$NAMO","$TRINQ",
    "$SPXA5R","$SPXA5","$SPXA10R","$SPXA20R","$SPXA50R","$SPXA200R",
    "$VIX","$VIX3M","$VVIX","$SKEW",
]

for symbol in SYMBOLS:
    try:
        params={"s":symbol,"f":"json","randomNumber":str(int(time.time()*1000))}
        headers=dict(UA)
        headers["Referer"]=f"https://stockcharts.com/sc3/ui/?s=%24{symbol.lstrip('$')}"
        r=requests.get("https://stockcharts.com/quotebrain/quotes",params=params,headers=headers,timeout=20)
        print("HTTP",symbol,r.status_code,r.url)
        r.raise_for_status()
        payload=r.json()
        print("QUOTE",symbol,json.dumps(payload,sort_keys=True)[:3000])
    except Exception as exc:
        print("ERROR",symbol,repr(exc))
