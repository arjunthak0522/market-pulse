#!/usr/bin/env python3
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'market_context.json'
HIST=ROOT/'data'/'history.json'
CBOE='https://cdn.cboe.com/api/global/us_indices/daily_prices/{symbol}_History.csv'


def load(path,default):
    try:return json.loads(path.read_text())
    except:return default


def cboe_series(symbol):
    df=pd.read_csv(CBOE.format(symbol=symbol))
    cols={str(c).strip().upper():c for c in df.columns}
    if 'DATE' not in cols:raise ValueError(f'{symbol}: DATE column missing')
    date_col=cols['DATE']
    value_col=cols.get('CLOSE') or cols.get(symbol.upper())
    if value_col is None:
        candidates=[c for c in df.columns if c!=date_col and pd.to_numeric(df[c],errors='coerce').notna().any()]
        if not candidates:raise ValueError(f'{symbol}: value column missing')
        value_col=candidates[-1]
    dates=pd.to_datetime(df[date_col],errors='coerce')
    vals=pd.to_numeric(df[value_col],errors='coerce')
    s=pd.Series(vals.values,index=dates).dropna().sort_index()
    s=s[~s.index.duplicated(keep='last')]
    if s.empty:raise ValueError(f'{symbol}: no usable observations')
    return s.astype(float)


def percentile(value,series,window=252):
    vals=[float(x) for x in series.tail(window).dropna().tolist()]
    if value is None or len(vals)<20:return None
    return round(100*sum(x<=float(value) for x in vals)/len(vals),1)


def main():
    d=load(OUT,{})
    h=load(HIST,{'breadth':[],'market':[],'put_call':[],'regime_history':[]})
    market_date=d.get('market_date')
    if not market_date:raise ValueError('market_context market_date missing')
    target=pd.Timestamp(market_date)
    vix=cboe_series('VIX');vix3m=cboe_series('VIX3M');vvix=cboe_series('VVIX');skew=cboe_series('SKEW')
    missing=[name for name,s in [('VIX',vix),('VIX3M',vix3m),('VVIX',vvix),('SKEW',skew)] if target not in s.index]
    if missing:raise ValueError(f'Options-risk data not aligned to {market_date}: missing {", ".join(missing)}')
    vx=float(vix.loc[target]);v3=float(vix3m.loc[target]);vv=float(vvix.loc[target]);sk=float(skew.loc[target]);ratio=vx/v3 if v3 else None
    term_state='Unavailable' if ratio is None else 'Inverted' if ratio>1 else 'Nearly flat' if ratio>=0.95 else 'Normal'
    vv_pct=percentile(vv,vvix.loc[:target],252)
    sk_pct=percentile(sk,skew.loc[:target],252)
    common=vix.index.intersection(vix3m.index).intersection(vvix.index).intersection(skew.index)
    common=common[common<=target][-252:]
    rows=[]
    for x in common:
        a=float(vix.loc[x]);b=float(vix3m.loc[x]);vvx=float(vvix.loc[x]);s=float(skew.loc[x])
        rows.append({'date':str(x.date()),'vix':round(a,3),'vix3m':round(b,3),'vix_vix3m_ratio':round(a/b,4) if b else None,'vvix':round(vvx,3),'skew':round(s,3)})
    d['options_risk']={
        'as_of':market_date,
        'vix3m':round(v3,2),
        'vix_vix3m_ratio':None if ratio is None else round(ratio,3),
        'term_structure':term_state,
        'vvix':round(vv,2),
        'vvix_percentile_252d':vv_pct,
        'skew':round(sk,2),
        'skew_percentile_252d':sk_pct,
        'source':'Cboe Global Indices daily history'
    }
    d.setdefault('component_status',{})['options_risk']={'as_of':market_date,'source':'Cboe Global Indices daily history'}
    h['options_risk']=rows
    OUT.write_text(json.dumps(d,indent=2)+'\n')
    HIST.write_text(json.dumps(h,indent=2)+'\n')
    print(json.dumps(d['options_risk'],indent=2))

if __name__=='__main__':main()
