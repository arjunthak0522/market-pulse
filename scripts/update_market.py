#!/usr/bin/env python3
import json,re
from datetime import datetime,timezone
from pathlib import Path
import numpy as np,pandas as pd,requests,yfinance as yf
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data'/'market_context.json';UA={'User-Agent':'Mozilla/5.0 MarketPulse/1.0'}
def old():
 try:return json.loads(OUT.read_text())
 except:return {'breadth':{},'vix':{},'equity_put_call':{},'etfs':{}}
def safe(prev,fn):
 try:return fn()
 except Exception as e:print('WARN',e);return prev
def rsi(c,p=14):
 d=c.diff();g=d.clip(lower=0).ewm(alpha=1/p,adjust=False).mean();l=(-d.clip(upper=0)).ewm(alpha=1/p,adjust=False).mean();rs=g/l.replace(0,np.nan);x=100-100/(1+rs);return float(x.iloc[-1])
def adx(df,p=14):
 h,l,c=df.High,df.Low,df.Close;up=h.diff();dn=-l.diff();pdm=up.where((up>dn)&(up>0),0);mdm=dn.where((dn>up)&(dn>0),0);tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1);atr=tr.ewm(alpha=1/p,adjust=False).mean();pdi=100*pdm.ewm(alpha=1/p,adjust=False).mean()/atr;mdi=100*mdm.ewm(alpha=1/p,adjust=False).mean()/atr;dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan);return float(dx.ewm(alpha=1/p,adjust=False).mean().iloc[-1])
def snap(sym):
 df=yf.download(sym,period='1y',interval='1d',auto_adjust=False,progress=False,threads=False)
 if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
 df=df.dropna(subset=['Close','High','Low']);c=df.Close.astype(float);last,prev=float(c.iloc[-1]),float(c.iloc[-2]);r=df.tail(14);hh,ll=float(r.High.max()),float(r.Low.min());wr=-100*(hh-last)/(hh-ll) if hh!=ll else -50;ma20=c.rolling(20).mean().iloc[-1];sd=c.rolling(20).std(ddof=0).iloc[-1];lo,hi=ma20-2*sd,ma20+2*sd;bb=(last-lo)/(hi-lo) if hi!=lo else .5;e12=c.ewm(span=12,adjust=False).mean();e26=c.ewm(span=26,adjust=False).mean();m=e12-e26;sig=m.ewm(span=9,adjust=False).mean();dist=lambda k:(last/float(c.rolling(k).mean().iloc[-1])-1)*100
 return {'price':round(last,4),'change_pct':round((last/prev-1)*100,4),'rsi14':round(rsi(c),3),'williams_r14':round(wr,3),'bollinger_pct_b':round(float(bb),4),'macd':round(float(m.iloc[-1]),4),'macd_signal':round(float(sig.iloc[-1]),4),'adx14':round(adx(df),3),'distance_ma20':round(dist(20),3),'distance_ma50':round(dist(50),3),'distance_ma200':round(dist(200),3),'market_date':str(df.index[-1].date())}
def putcall():
 t=BeautifulSoup(requests.get('https://www.cboe.com/markets/us/options/market-statistics/daily/',headers=UA,timeout=30).text,'html.parser').get_text(' ',strip=True);m=re.search(r'EQUITY PUT/CALL RATIO\s+([0-9]+(?:\.[0-9]+)?)',t,re.I)
 if not m:raise ValueError('Cboe put/call not found')
 return float(m.group(1))
def breadth():
 syms=[str(x).replace('.','-') for x in pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0].Symbol.dropna()];raw=yf.download(syms,period='15mo',interval='1d',auto_adjust=False,progress=False,threads=True,group_by='ticker');above={5:0,20:0,50:0,200:0};eligible={5:0,20:0,50:0,200:0};adv=dec=unch=highs=lows=0
 for s in syms:
  try:
   fr=raw[s] if isinstance(raw.columns,pd.MultiIndex) else raw;c=fr.Close.dropna().astype(float)
   if len(c)<2:continue
   last,prev=float(c.iloc[-1]),float(c.iloc[-2]);adv+=last>prev;dec+=last<prev;unch+=last==prev
   for k in above:
    if len(c)>=k:eligible[k]+=1;above[k]+=last>float(c.tail(k).mean())
   if len(c)>=200:
    w=c.tail(min(252,len(c)));highs+=last>=float(w.max());lows+=last<=float(w.min())
  except:pass
 return {'above_5d':round(100*above[5]/eligible[5],2),'above_20d':round(100*above[20]/eligible[20],2),'above_50d':round(100*above[50]/eligible[50],2),'above_200d':round(100*above[200]/eligible[200],2),'advancers':int(adv),'decliners':int(dec),'unchanged':int(unch),'new_highs_52w':int(highs),'new_lows_52w':int(lows),'source':'S&P 500 constituent closes via Yahoo Finance'}
def main():
 p=old();spy=safe((p.get('etfs')or{}).get('SPY',{}),lambda:snap('SPY'));qqq=safe((p.get('etfs')or{}).get('QQQ',{}),lambda:snap('QQQ'));vx=safe((p.get('vix')or{}).get('value'),lambda:float(yf.download('^VIX',period='5d',interval='1d',auto_adjust=False,progress=False)['Close'].dropna().iloc[-1]));pc=safe((p.get('equity_put_call')or{}).get('value'),putcall);br=safe(p.get('breadth',{}),breadth);date=spy.get('market_date') or p.get('market_date');out={'generated_at':datetime.now(timezone.utc).isoformat(),'market_date':date,'breadth':br,'vix':{'value':round(float(vx),2) if vx is not None else None,'source':'Cboe VIX via Yahoo Finance'},'equity_put_call':{'value':pc,'source':'Cboe Daily Market Statistics'},'etfs':{'SPY':spy,'QQQ':qqq}};OUT.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()