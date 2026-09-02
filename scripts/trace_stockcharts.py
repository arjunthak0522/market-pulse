#!/usr/bin/env python3
"""Audit StockCharts QuoteBrain support for Market Pulse live inputs."""
import json
import time
import requests

UA={"User-Agent":"Mozilla/5.0 MarketPulse/1.0","Accept":"application/json,text/plain,*/*","Referer":"https://stockcharts.com/"}
SYMBOLS=[
    "$CPCE","$NYADV","$NYDEC","$NYUPV","$NYDNV","$NYHGH","$NYLOW","$NYTOT","$NYMO","$TRIN",
    "$NAADV","$NADEC","$NAUPV","$NADNV","$NAHGH","$NALOW","$NATOT","$NAMO","$TRINQ",
    "$SPXA5R","$SPXA5","$SPXA10R","$SPXA20R","$SPXA50R","$SPXA200R","$VIX","$VIX3M","$VVIX","$SKEW",
]
for symbol in SYMBOLS:
    try:
        params={"s":symbol,"f":"json","randomNumber":str(int(time.time()*1000))}
        r=requests.get("https://stockcharts.com/quotebrain/quotes",params=params,headers=UA,timeout=20)
        print("HTTP",symbol,r.status_code,"ACAO=",r.headers.get("access-control-allow-origin"),"ACAC=",r.headers.get("access-control-allow-credentials"))
        print("QUOTE",symbol,r.text[:1600])
    except Exception as exc:
        print("ERROR",symbol,repr(exc))

for symbol in ("$NYADV","$NYDEC","$NAADV","$NADEC"):
    for start in ("20260601","2026-06-01"):
        try:
            params={"ticker":symbol,"start":start,"barwidth":"D","out":"text","memberrt":"false","randomNumber":str(int(time.time()*1000))}
            r=requests.get("https://stockcharts.com/quotebrain/pastdata",params=params,headers=UA,timeout=20)
            print("PAST",symbol,start,r.status_code,r.headers.get("content-type"),repr(r.text[:1600]))
        except Exception as exc:
            print("PAST_ERROR",symbol,start,repr(exc))
