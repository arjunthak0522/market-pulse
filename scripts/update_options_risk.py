#!/usr/bin/env python3
import json
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'market_context.json'
HIST=ROOT/'data'/'history.json'


def load(path,default):
    try:return json.loads(path.read_text())
    except:return default


def close_series(sym,period='18mo'):
    df=yf.download(sym,period=period,interval='1d',auto_adjust=False,progress=False,threads=False)
    if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
    c=df['Close'].dropna().astype(float)
    if c.empty:raise ValueError(f'No data for {sym}')
    return c


def percentile(value,series,window=252):
    vals=[float(x) for x in series.tail(window).dropna().tolist()]
    if value is None or len(vals)<20:return None
    return round(100*sum(x<=float(value) for x in vals)/len(vals),1)


def main():
    d=load(OUT,{})
    h=load(HIST,{'breadth':[],'market':[],'put_call':[],'regime_history':[]})
    vix=close_series('^VIX')
    vix3m=close_series('^VIX3M')
    skew=close_series('^SKEW')
    common=vix.index.intersection(vix3m.index).intersection(skew.index)
    if common.empty:raise ValueError('No common VIX/VIX3M/SKEW market date')
    dt=common[-1]
    vx=float(vix.loc[dt]);v3=float(vix3m.loc[dt]);sk=float(skew.loc[dt])
    ratio=vx/v3 if v3 else None
    if ratio is None:term_state='Unavailable'
    elif ratio>1:term_state='Inverted'
    elif ratio>=0.95:term_state='Nearly flat'
    else:term_state='Normal'
    sk_pct=percentile(sk,skew,252)
    rows=[]
    for x in common[-252:]:
        a=float(vix.loc[x]);b=float(vix3m.loc[x]);s=float(skew.loc[x])
        rows.append({'date':str(x.date()),'vix':round(a,3),'vix3m':round(b,3),'vix_vix3m_ratio':round(a/b,4) if b else None,'skew':round(s,3)})
    d['options_risk']={
        'as_of':str(dt.date()),
        'vix3m':round(v3,2),
        'vix_vix3m_ratio':None if ratio is None else round(ratio,3),
        'term_structure':term_state,
        'skew':round(sk,2),
        'skew_percentile_252d':sk_pct,
        'source':'Cboe VIX3M and SKEW indexes via Yahoo Finance'
    }
    d.setdefault('component_status',{})['options_risk']={'as_of':str(dt.date()),'source':'Cboe VIX3M and SKEW indexes via Yahoo Finance'}
    h['options_risk']=rows
    OUT.write_text(json.dumps(d,indent=2)+'\n')
    HIST.write_text(json.dumps(h,indent=2)+'\n')
    print(json.dumps(d['options_risk'],indent=2))

if __name__=='__main__':main()
