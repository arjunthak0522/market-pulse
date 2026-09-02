#!/usr/bin/env python3
import re
from urllib.parse import urljoin
import requests

UA={"User-Agent":"Mozilla/5.0"}
page="https://stockcharts.com/sc3/ui/?s=%24TRIN"
r=requests.get(page,headers=UA,timeout=30)
r.raise_for_status()
print("PAGE",r.status_code,len(r.text),r.url)
scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)',r.text,re.I)
print("SCRIPTS",scripts)
for src in scripts:
    url=urljoin(r.url,src)
    try:
        x=requests.get(url,headers=UA,timeout=30)
        print("SCRIPT",url,x.status_code,len(x.text))
        text=x.text
        needles=["quotebrain/quotes","quotebrain/pastdata","quotebrain/ismarketopen"]
        for needle in needles:
            start=0
            while True:
                i=text.find(needle,start)
                if i<0: break
                lo=max(0,i-1800); hi=min(len(text),i+2200)
                print("CONTEXT",needle,text[lo:hi])
                start=i+len(needle)
        for pat in [r'new URLSearchParams\([^;]{0,1000}',r'URLSearchParams\([^;]{0,1000}',r'quotebrain[^`"\']{0,500}']:
            for hit in re.findall(pat,text,re.I)[:50]:
                print("PARAM_HIT",hit[:1200])
    except Exception as exc:
        print("SCRIPT_ERROR",url,exc)
