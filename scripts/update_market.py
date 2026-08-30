#!/usr/bin/env python3
import json,re
from datetime import datetime,timezone
from pathlib import Path
import numpy as np,pandas as pd,requests,yfinance as yf
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'market_context.json'
HIST=ROOT/'data'/'history.json'
UA={'User-Agent':'Mozilla/5.0 MarketPulse/1.0'}

def old():
    try:return json.loads(OUT.read_text())
    except:return {'breadth':{},'vix':{},'equity_put_call':{},'etfs':{}}

def safe(prev,fn):
    try:return fn()
    except Exception as e:
        print('WARN',e)
        return prev

def rsi_series(c,p=14):
    d=c.diff();g=d.clip(lower=0).ewm(alpha=1/p,adjust=False).mean();l=(-d.clip(upper=0)).ewm(alpha=1/p,adjust=False).mean();rs=g/l.replace(0,np.nan)
    return 100-100/(1+rs)

def adx(df,p=14):
    h,l,c=df.High,df.Low,df.Close;up=h.diff();dn=-l.diff();pdm=up.where((up>dn)&(up>0),0);mdm=dn.where((dn>up)&(dn>0),0)
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1);atr=tr.ewm(alpha=1/p,adjust=False).mean();pdi=100*pdm.ewm(alpha=1/p,adjust=False).mean()/atr;mdi=100*mdm.ewm(alpha=1/p,adjust=False).mean()/atr;dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    return float(dx.ewm(alpha=1/p,adjust=False).mean().iloc[-1])

def snap(sym):
    df=yf.download(sym,period='18mo',interval='1d',auto_adjust=False,progress=False,threads=False)
    if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
    df=df.dropna(subset=['Close','High','Low']);c=df.Close.astype(float);last,prev=float(c.iloc[-1]),float(c.iloc[-2]);r=df.tail(14);hh,ll=float(r.High.max()),float(r.Low.min());wr=-100*(hh-last)/(hh-ll) if hh!=ll else -50
    ma20=c.rolling(20).mean().iloc[-1];sd=c.rolling(20).std(ddof=0).iloc[-1];lo,hi=ma20-2*sd,ma20+2*sd;bb=(last-lo)/(hi-lo) if hi!=lo else .5;e12=c.ewm(span=12,adjust=False).mean();e26=c.ewm(span=26,adjust=False).mean();m=e12-e26;sig=m.ewm(span=9,adjust=False).mean();dist=lambda k:(last/float(c.rolling(k).mean().iloc[-1])-1)*100
    hi52=float(c.tail(min(252,len(c))).max());d52=(last/hi52-1)*100
    return {'price':round(last,4),'change_pct':round((last/prev-1)*100,4),'rsi14':round(float(rsi_series(c).iloc[-1]),3),'williams_r14':round(wr,3),'bollinger_pct_b':round(float(bb),4),'macd':round(float(m.iloc[-1]),4),'macd_signal':round(float(sig.iloc[-1]),4),'adx14':round(adx(df),3),'distance_ma20':round(dist(20),3),'distance_ma50':round(dist(50),3),'distance_ma200':round(dist(200),3),'distance_52w_high':round(d52,3),'market_date':str(df.index[-1].date())}

def putcall():
    t=BeautifulSoup(requests.get('https://www.cboe.com/markets/us/options/market-statistics/daily/',headers=UA,timeout=30).text,'html.parser').get_text(' ',strip=True);m=re.search(r'EQUITY PUT/CALL RATIO\s+([0-9]+(?:\.[0-9]+)?)',t,re.I)
    if not m:raise ValueError('Cboe put/call not found')
    return float(m.group(1))

def breadth():
    constituents=pd.read_csv('https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv')
    syms=[str(x).replace('.','-') for x in constituents.Symbol.dropna()]
    raw=yf.download(syms,period='18mo',interval='1d',auto_adjust=False,progress=False,threads=True,group_by='ticker')
    closes={};adv=dec=unch=highs=lows=0
    for s in syms:
        try:
            fr=raw[s] if isinstance(raw.columns,pd.MultiIndex) else raw;c=fr.Close.dropna().astype(float)
            if len(c)<2:continue
            closes[s]=c;last,prev=float(c.iloc[-1]),float(c.iloc[-2]);adv+=last>prev;dec+=last<prev;unch+=last==prev
            if len(c)>=200:
                w=c.tail(min(252,len(c)));highs+=last>=float(w.max());lows+=last<=float(w.min())
        except:pass
    cm=pd.DataFrame(closes).sort_index()
    if cm.shape[1]<400:raise ValueError(f'Breadth universe incomplete: only {cm.shape[1]} symbols')
    hist=pd.DataFrame(index=cm.index)
    for k in [5,20,50,200]:
        ma=cm.rolling(k,min_periods=k).mean();eligible=cm.notna()&ma.notna();above=(cm>ma)&eligible
        hist[f'above_{k}d']=100*above.sum(axis=1)/eligible.sum(axis=1).replace(0,np.nan)
    hist=hist.dropna(subset=['above_200d']).tail(252)
    last=hist.iloc[-1]
    current={k:round(float(last[k]),2) for k in ['above_5d','above_20d','above_50d','above_200d']}
    current.update({'advancers':int(adv),'decliners':int(dec),'unchanged':int(unch),'new_highs_52w':int(highs),'new_lows_52w':int(lows),'source':'S&P 500 constituent closes via Yahoo Finance'})
    records=[]
    for dt,row in hist.iterrows():
        records.append({'date':str(dt.date()),**{k:round(float(row[k]),2) for k in ['above_5d','above_20d','above_50d','above_200d']}})
    return current,records

def leadership_history():
    raw=yf.download(['SPY','QQQ','^VIX'],period='18mo',interval='1d',auto_adjust=False,progress=False,threads=True,group_by='ticker')
    def close(sym):
        x=raw[sym]['Close'] if isinstance(raw.columns,pd.MultiIndex) else raw['Close'];return x.dropna().astype(float)
    spy,qqq,vix=close('SPY'),close('QQQ'),close('^VIX');idx=spy.index.intersection(qqq.index);ratio=(qqq.reindex(idx)/spy.reindex(idx));rel20=(ratio/ratio.shift(20)-1)*100
    frame=pd.DataFrame({'spy':spy.reindex(idx),'qqq':qqq.reindex(idx),'relative_strength_20d':rel20,'vix':vix.reindex(idx)}).dropna(subset=['spy','qqq']).tail(252)
    rec=[]
    for dt,row in frame.iterrows():
        rec.append({'date':str(dt.date()),'spy':round(float(row.spy),4),'qqq':round(float(row.qqq),4),'relative_strength_20d':None if pd.isna(row.relative_strength_20d) else round(float(row.relative_strength_20d),3),'vix':None if pd.isna(row.vix) else round(float(row.vix),2)})
    latest=next((x['relative_strength_20d'] for x in reversed(rec) if x['relative_strength_20d'] is not None),None)
    return latest,rec

def main():
    p=old();spy=safe((p.get('etfs')or{}).get('SPY',{}),lambda:snap('SPY'));qqq=safe((p.get('etfs')or{}).get('QQQ',{}),lambda:snap('QQQ'))
    vx=safe((p.get('vix')or{}).get('value'),lambda:float(np.asarray(yf.download('^VIX',period='5d',interval='1d',auto_adjust=False,progress=False)['Close'].dropna()).reshape(-1)[-1]));pc=safe((p.get('equity_put_call')or{}).get('value'),putcall)
    br_res=safe((p.get('breadth',{}),[]),breadth)
    if isinstance(br_res,tuple):br,bhist=br_res
    else:br,bhist=br_res,[]
    lead_res=safe((None,[]),leadership_history)
    if isinstance(lead_res,tuple):lead,lhist=lead_res
    else:lead,lhist=None,[]
    date=spy.get('market_date') or p.get('market_date')
    out={'generated_at':datetime.now(timezone.utc).isoformat(),'market_date':date,'breadth':br,'vix':{'value':round(float(vx),2) if vx is not None else None,'source':'Cboe VIX via Yahoo Finance'},'equity_put_call':{'value':pc,'source':'Cboe Daily Market Statistics'},'relative_strength':{'qqq_vs_spy_20d':lead},'etfs':{'SPY':spy,'QQQ':qqq}}
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    hist={'generated_at':out['generated_at'],'market_date':date,'breadth':bhist,'market':lhist}
    HIST.write_text(json.dumps(hist,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
