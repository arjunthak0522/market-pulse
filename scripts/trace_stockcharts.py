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
        pats=[r'https?://[^"\'\s)]+',r'/api/[^"\'\s)]+',r'quote[^"\'\s]{0,120}',r'xignite[^"\'\s]{0,120}',r'symbol[^"\'\s]{0,120}']
        hits=[]
        for pat in pats:
            hits.extend(re.findall(pat,text,re.I))
        for h in hits[:120]:
            if any(k in h.lower() for k in ('api','quote','xignite','symbol','price')):
                print("HIT",h[:300])
    except Exception as exc:
        print("SCRIPT_ERROR",url,exc)
