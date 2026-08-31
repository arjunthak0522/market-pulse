#!/usr/bin/env python3
import json,re
from datetime import datetime,timezone,timedelta
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

def old_hist():
    try:return json.loads(HIST.read_text())
    except:return {'breadth':[],'market':[],'put_call':[],'regime_history':[]}

def safe(prev,fn):
    try:return fn()
    except Exception as e:
        print('WARN',e)
        return prev

def rsi_series(c,p=14):
    d=c.diff();g=d.clip(lower=0).ewm(alpha=1/p,adjust=False).mean();l=(-d.clip(upper=0)).ewm(alpha=1/p,adjust=False).mean();rs=g/l.replace(0,np.nan)
    return 100-100/(1+rs)

def rsi_frame(frame,p=14):
    d=frame.diff();g=d.clip(lower=0).ewm(alpha=1/p,adjust=False).mean();l=(-d.clip(upper=0)).ewm(alpha=1/p,adjust=False).mean();rs=g/l.replace(0,np.nan)
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

def parse_putcall_text(text):
    m=re.search(r'EQUITY PUT/CALL RATIO\s+([0-9]+(?:\.[0-9]+)?)',text,re.I)
    if not m:raise ValueError('Cboe put/call not found')
    return float(m.group(1))

def putcall():
    text=BeautifulSoup(requests.get('https://www.cboe.com/markets/us/options/market-statistics/daily/',headers=UA,timeout=30).text,'html.parser').get_text(' ',strip=True)
    return parse_putcall_text(text)

def putcall_for_date(ds):
    url=f'https://www.cboe.com/markets/us/options/market-statistics/daily?dt={ds}'
    text=BeautifulSoup(requests.get(url,headers=UA,timeout=15).text,'html.parser').get_text(' ',strip=True)
    return parse_putcall_text(text)

def putcall_history(existing,market_date,current):
    by_date={str(x.get('date')):x for x in (existing or []) if x.get('date') and x.get('value') is not None}
    if market_date and current is not None:by_date[market_date]={'date':market_date,'value':round(float(current),4)}
    if len(by_date)<40 and market_date:
        end=datetime.strptime(market_date,'%Y-%m-%d').date();tries=0;d=end
        while len(by_date)<63 and tries<95:
            ds=str(d);tries+=1
            if d.weekday()<5 and ds not in by_date:
                try:by_date[ds]={'date':ds,'value':round(float(putcall_for_date(ds)),4)}
                except Exception as e:print('WARN putcall history',ds,e)
            d-=timedelta(days=1)
    rows=sorted(by_date.values(),key=lambda x:x['date'])[-252:]
    vals=[float(x['value']) for x in rows[-60:] if x.get('value') is not None]
    percentile=None
    if current is not None and len(vals)>=20:percentile=100*sum(v<=float(current) for v in vals)/len(vals)
    return rows,None if percentile is None else round(percentile,1)

def breadth():
    constituents=pd.read_csv('https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv')
    syms=[str(x).replace('.','-') for x in constituents.Symbol.dropna()]
    raw=yf.download(syms,period='18mo',interval='1d',auto_adjust=False,progress=False,threads=True,group_by='ticker')
    closes={};volumes={};adv=dec=unch=highs=lows=0
    for s in syms:
        try:
            fr=raw[s] if isinstance(raw.columns,pd.MultiIndex) else raw;c=fr.Close.dropna().astype(float)
            if len(c)<2:continue
            closes[s]=c
            try:volumes[s]=fr.Volume.astype(float).reindex(c.index)
            except:pass
            last,prev=float(c.iloc[-1]),float(c.iloc[-2]);adv+=last>prev;dec+=last<prev;unch+=last==prev
            if len(c)>=200:
                w=c.tail(min(252,len(c)));highs+=last>=float(w.max());lows+=last<=float(w.min())
        except:pass
    cm=pd.DataFrame(closes).sort_index()
    if cm.shape[1]<400:raise ValueError(f'Breadth universe incomplete: only {cm.shape[1]} symbols')
    vm=pd.DataFrame(volumes).reindex(index=cm.index,columns=cm.columns)
    hist=pd.DataFrame(index=cm.index)
    for k in [5,20,50,200]:
        ma=cm.rolling(k,min_periods=k).mean();eligible=cm.notna()&ma.notna();above=(cm>ma)&eligible
        hist[f'above_{k}d']=100*above.sum(axis=1)/eligible.sum(axis=1).replace(0,np.nan)
    diff=cm.diff();adv_mask=diff>0;dec_mask=diff<0
    adv_count=adv_mask.sum(axis=1).astype(float);dec_count=dec_mask.sum(axis=1).astype(float);active=(adv_count+dec_count).replace(0,np.nan)
    hist['advancers']=adv_count;hist['decliners']=dec_count;hist['ad_net']=adv_count-dec_count;hist['ad_ratio']=adv_count/dec_count.replace(0,np.nan);hist['advancing_pct']=100*adv_count/active
    adv_vol=vm.where(adv_mask).sum(axis=1,min_count=1);dec_vol=vm.where(dec_mask).sum(axis=1,min_count=1);vol_ratio=adv_vol/dec_vol.replace(0,np.nan);hist['trin']=(hist['ad_ratio']/vol_ratio.replace(0,np.nan)).replace([np.inf,-np.inf],np.nan)
    rf=rsi_frame(cm,14);eligible_rsi=rf.notna();den=eligible_rsi.sum(axis=1).replace(0,np.nan);hist['rsi_below_30']=100*((rf<30)&eligible_rsi).sum(axis=1)/den;hist['rsi_above_70']=100*((rf>70)&eligible_rsi).sum(axis=1)/den
    hist=hist.dropna(subset=['above_200d']).tail(252);last=hist.iloc[-1];prev=hist.iloc[-2] if len(hist)>1 else last
    current={k:round(float(last[k]),2) for k in ['above_5d','above_20d','above_50d','above_200d']}
    current.update({'advancers':int(adv),'decliners':int(dec),'unchanged':int(unch),'new_highs_52w':int(highs),'new_lows_52w':int(lows),'ad_net':int(last.ad_net),'ad_ratio':round(float(last.ad_ratio),3) if pd.notna(last.ad_ratio) else None,'advancing_pct':round(float(last.advancing_pct),1) if pd.notna(last.advancing_pct) else None,'ad_ratio_5d':round(float(hist.ad_ratio.tail(5).mean()),3) if hist.ad_ratio.tail(5).notna().any() else None,'rsi_below_30':round(float(last.rsi_below_30),1) if pd.notna(last.rsi_below_30) else None,'rsi_below_30_prev':round(float(prev.rsi_below_30),1) if pd.notna(prev.rsi_below_30) else None,'rsi_above_70':round(float(last.rsi_above_70),1) if pd.notna(last.rsi_above_70) else None,'trin':round(float(last.trin),3) if pd.notna(last.trin) else None,'trin_prev':round(float(prev.trin),3) if pd.notna(prev.trin) else None,'trin_method':'Arms formula using S&P 500 constituent issues and volume','source':'S&P 500 constituent closes and volume via Yahoo Finance'})
    records=[];cols=['above_5d','above_20d','above_50d','above_200d','advancers','decliners','ad_net','ad_ratio','advancing_pct','rsi_below_30','rsi_above_70','trin']
    for dt,row in hist.iterrows():
        rec={'date':str(dt.date())}
        for k in cols:
            v=row.get(k);rec[k]=None if pd.isna(v) else (int(v) if k in ['advancers','decliners','ad_net'] else round(float(v),3))
        records.append(rec)
    return current,records

def leadership_history():
    raw=yf.download(['SPY','QQQ','^VIX'],period='18mo',interval='1d',auto_adjust=False,progress=False,threads=True,group_by='ticker')
    def close(sym):
        x=raw[sym]['Close'] if isinstance(raw.columns,pd.MultiIndex) else raw['Close'];return x.dropna().astype(float)
    spy,qqq,vix=close('SPY'),close('QQQ'),close('^VIX');idx=spy.index.intersection(qqq.index);ratio=(qqq.reindex(idx)/spy.reindex(idx));rel20=(ratio/ratio.shift(20)-1)*100
    frame=pd.DataFrame({'spy':spy.reindex(idx),'qqq':qqq.reindex(idx),'relative_strength_20d':rel20,'vix':vix.reindex(idx)}).dropna(subset=['spy','qqq']).tail(252);rec=[]
    for dt,row in frame.iterrows():rec.append({'date':str(dt.date()),'spy':round(float(row.spy),4),'qqq':round(float(row.qqq),4),'relative_strength_20d':None if pd.isna(row.relative_strength_20d) else round(float(row.relative_strength_20d),3),'vix':None if pd.isna(row.vix) else round(float(row.vix),2)})
    latest=next((x['relative_strength_20d'] for x in reversed(rec) if x['relative_strength_20d'] is not None),None)
    return latest,rec

def official_regime(br,spy,qqq,vix,pc):
    b5,b50,b200=br.get('above_5d'),br.get('above_50d'),br.get('above_200d');s20,q20=spy.get('distance_ma20'),qqq.get('distance_ma20');s50,q50=spy.get('distance_ma50'),qqq.get('distance_ma50');s200,q200=spy.get('distance_ma200'),qqq.get('distance_ma200')
    primary=(b200 is None or b200>=60) and (s200 is None or s200>=0) and (q200 is None or q200>=0);struct=(b200 is not None and b200<40) or (s200 is not None and s200<0 and q200 is not None and q200<0);stress=(vix is not None and vix>=25) or (pc is not None and pc>=1);pressure=(b50 is not None and b50<40) or (s50 is not None and s50<0) or (q50 is not None and q50<0)
    if struct and stress:return 'Risk-off / structural weakness'
    if struct:return 'Primary trend damage'
    if b5 is not None and b5<15 and stress:return 'Broad washout'
    if b5 is not None and b5<25 and primary:return 'Washout developing'
    if pressure and primary:return 'Trend deterioration'
    if primary and ((b5 is not None and b5<45) or (s20 is not None and s20<0) or (q20 is not None and q20<0)):return 'Healthy pullback'
    if primary and b50 is not None and b50<50:return 'Narrow / fragile rally'
    if primary:return 'Healthy uptrend'
    return 'Mixed / transitional market'

def main():
    p=old();ph=old_hist();spy=safe((p.get('etfs')or{}).get('SPY',{}),lambda:snap('SPY'));qqq=safe((p.get('etfs')or{}).get('QQQ',{}),lambda:snap('QQQ'))
    vx=safe((p.get('vix')or{}).get('value'),lambda:float(np.asarray(yf.download('^VIX',period='5d',interval='1d',auto_adjust=False,progress=False)['Close'].dropna()).reshape(-1)[-1]));pc=safe((p.get('equity_put_call')or{}).get('value'),putcall)
    br_res=safe((p.get('breadth',{}),ph.get('breadth',[])),breadth);br,bhist=br_res if isinstance(br_res,tuple) else (br_res,ph.get('breadth',[]))
    lead_res=safe((None,ph.get('market',[])),leadership_history);lead,lhist=lead_res if isinstance(lead_res,tuple) else (None,ph.get('market',[]))
    date=spy.get('market_date') or p.get('market_date');pc_hist,pc_pct=safe((ph.get('put_call',[]),(p.get('equity_put_call')or{}).get('percentile_60d')),lambda:putcall_history(ph.get('put_call',[]),date,pc))
    now=datetime.now(timezone.utc).isoformat();reg=official_regime(br,spy,qqq,vx,pc)
    out={'generated_at':now,'market_date':date,'breadth':br,'vix':{'value':round(float(vx),2) if vx is not None else None,'source':'Cboe VIX via Yahoo Finance'},'equity_put_call':{'value':pc,'percentile_60d':pc_pct,'history_count':len(pc_hist),'source':'Cboe Daily Market Statistics'},'relative_strength':{'qqq_vs_spy_20d':lead},'etfs':{'SPY':spy,'QQQ':qqq},'official_regime':reg,'component_status':{'breadth':{'as_of':date,'source':'S&P 500 constituent closes and volume'},'SPY':{'as_of':spy.get('market_date')},'QQQ':{'as_of':qqq.get('market_date')},'VIX':{'as_of':date},'put_call':{'as_of':date}}}
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    rh=[x for x in ph.get('regime_history',[]) if x.get('date')!=date]
    if date:rh.append({'date':date,'regime':reg,'recorded_at':now})
    rh=sorted(rh,key=lambda x:x.get('date',''))[-1000:]
    hist={'generated_at':now,'market_date':date,'breadth':bhist,'market':lhist,'put_call':pc_hist,'regime_history':rh}
    HIST.write_text(json.dumps(hist,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
