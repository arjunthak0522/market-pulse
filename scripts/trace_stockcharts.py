#!/usr/bin/env python3
import time
import requests

UA={"User-Agent":"Mozilla/5.0","Accept":"application/json,text/plain,*/*","Referer":"https://stockcharts.com/"}
url="https://stockcharts.com/quotebrain/quotes"
symbols=[
    "$TRIN","$TRINQ","$CPCE","$NAMO","$NYMO",
    "$NYHGH","$NYLOW","$NAHGH","$NALOW",
    "$SPXA5R","$SPXA5","$SPXA10R","$SPXA20R","$SPXA50R","$SPXA200R",
    "$VIX","$VIX3M","$VVIX","$SKEW",
]
for symbol in symbols:
    try:
        r=requests.get(url,params={"s":symbol,"f":"json","randomNumber":str(int(time.time()*1000))},headers=UA,timeout=20)
        print("SYMBOL",symbol,"HTTP",r.status_code,"TEXT",r.text[:1200])
    except Exception as exc:
        print("ERROR",symbol,repr(exc))
