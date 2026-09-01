#!/usr/bin/env python3
import json
from pathlib import Path
import pandas as pd
import yfinance as yf

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'global_liquidity.json'
FRED='https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}'

SERIES={
    'fed':('WALCL','Federal Reserve total assets'),
    'ecb':('ECBASSETSW','ECB total assets'),
    'boj':('JPNASSETS','Bank of Japan total assets'),
}


def fred_series(series):
    df=pd.read_csv(FRED.format(series=series))
    if df.shape[1]<2:raise ValueError(f'{series}: malformed FRED response')
    dates=pd.to_datetime(df.iloc[:,0],errors='coerce')
    vals=pd.to_numeric(df.iloc[:,1],errors='coerce')
    s=pd.Series(vals.values,index=dates).dropna().sort_index()
    s=s[~s.index.duplicated(keep='last')]
    if s.empty:raise ValueError(f'{series}: no observations')
    return s.astype(float)


def dxy_series():
    df=yf.download('DX-Y.NYB',period='3y',interval='1d',auto_adjust=False,progress=False,threads=False)
    if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
    s=pd.to_numeric(df['Close'],errors='coerce').dropna()
    s.index=pd.to_datetime(s.index).tz_localize(None)
    if s.empty:raise ValueError('DXY: no observations')
    return s.astype(float)


def signal(x,threshold):
    if pd.isna(x):return None
    if x>threshold:return 1
    if x<-threshold:return -1
    return 0


def main():
    raw={k:fred_series(v[0]) for k,v in SERIES.items()}
    raw['dxy']=dxy_series()
    start=max(s.index.min() for s in raw.values())
    end=max(s.index.max() for s in raw.values())
    idx=pd.date_range(start,end,freq='D')
    frame=pd.DataFrame({k:s.reindex(idx).ffill() for k,s in raw.items()}).dropna()
    if len(frame)<180:raise ValueError('Insufficient liquidity history')

    roc=100*(frame/frame.shift(91)-1)
    scored=pd.DataFrame(index=roc.index)
    scored['fed']=roc['fed'].map(lambda x:signal(x,.5))
    scored['ecb']=roc['ecb'].map(lambda x:signal(x,.5))
    scored['boj']=roc['boj'].map(lambda x:signal(x,.5))
    scored['dxy']=roc['dxy'].map(lambda x:-signal(x,2.0) if signal(x,2.0) is not None else None)
    scored['score']=scored.mean(axis=1,skipna=False)
    valid=scored.dropna(subset=['score'])
    if valid.empty:raise ValueError('Liquidity score unavailable')

    dt=valid.index[-1]
    current=float(valid.loc[dt,'score'])
    prev_idx=valid.index[valid.index<=dt-pd.Timedelta(days=28)]
    prior=float(valid.loc[prev_idx[-1],'score']) if len(prev_idx) else current
    delta=current-prior
    backdrop='SUPPORTIVE' if current>=.5 else 'UNSUPPORTIVE' if current<=-.5 else 'MIXED'
    momentum='IMPROVING' if delta>=.25 else 'DETERIORATING' if delta<=-.25 else 'STABLE'

    components=[]
    labels={k:v[1] for k,v in SERIES.items()}
    labels['dxy']='U.S. dollar direction'
    for k in ['fed','ecb','boj','dxy']:
        change=float(roc.loc[dt,k])
        sig=int(valid.loc[dt,k])
        components.append({
            'id':k,
            'label':labels[k],
            'change_3m_pct':round(change,2),
            'contribution':'supportive' if sig>0 else 'tightening' if sig<0 else 'neutral',
            'source':SERIES[k][0]+' via FRED' if k in SERIES else 'DXY via Yahoo Finance'
        })

    hist=[]
    for x,row in valid.tail(365).iterrows():
        hist.append({'date':str(x.date()),'score':round(float(row.score),3)})

    out={
        'as_of':str(dt.date()),
        'backdrop':backdrop,
        'score':round(current,3),
        'momentum':momentum,
        'score_change_4w':round(delta,3),
        'methodology':'Equal-weight directional proxy: 3-month change in Fed, ECB and BOJ total assets plus inverse 3-month U.S. dollar direction. Central-bank moves use +/-0.5% neutral bands; DXY uses +/-2%.',
        'components':components,
        'history':hist,
        'limitations':'This is a transparent liquidity proxy, not a proprietary global-liquidity index or deterministic market forecast. PBOC is excluded until a current reliable source is available.'
    }
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
