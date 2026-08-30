#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf
import pandas_market_calendars as mcal

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'live.json'
NY=ZoneInfo('America/New_York')
CT=ZoneInfo('America/Chicago')

def market_open_now(now_utc):
    cal=mcal.get_calendar('NYSE')
    day=now_utc.astimezone(NY).date()
    sched=cal.schedule(start_date=day,end_date=day)
    if sched.empty:return False,None,None
    op=sched.iloc[0]['market_open'].to_pydatetime().astimezone(timezone.utc)
    cl=sched.iloc[0]['market_close'].to_pydatetime().astimezone(timezone.utc)
    return op<=now_utc<=cl,op,cl

def last_price(sym):
    x=yf.download(sym,period='5d',interval='5m',auto_adjust=False,progress=False,threads=False)
    if isinstance(x.columns,pd.MultiIndex):x.columns=x.columns.get_level_values(0)
    x=x.dropna(subset=['Close'])
    if x.empty:raise ValueError(f'No intraday data for {sym}')
    return float(x.Close.iloc[-1]), x.index[-1]

def prev_close(sym):
    x=yf.download(sym,period='7d',interval='1d',auto_adjust=False,progress=False,threads=False)
    if isinstance(x.columns,pd.MultiIndex):x.columns=x.columns.get_level_values(0)
    x=x.dropna(subset=['Close'])
    if len(x)<2:raise ValueError(f'No daily history for {sym}')
    return float(x.Close.iloc[-2])

def main():
    now=datetime.now(timezone.utc)
    is_open,op,cl=market_open_now(now)
    if not is_open:
        print('Market is closed; no intraday update written.')
        return
    data={}
    stamps=[]
    for sym in ['SPY','QQQ']:
        px,ts=last_price(sym); pc=prev_close(sym); stamps.append(ts)
        data[sym]={'price':round(px,4),'change_pct':round((px/pc-1)*100,4),'previous_close':round(pc,4)}
    vx,vx_ts=last_price('^VIX'); stamps.append(vx_ts)
    stamp=max(stamps)
    if getattr(stamp,'tzinfo',None) is None: stamp=stamp.tz_localize('UTC')
    stamp=stamp.to_pydatetime().astimezone(timezone.utc)
    out={
      'status':'market_open',
      'generated_at':now.isoformat(),
      'market_date':now.astimezone(NY).date().isoformat(),
      'data_time':stamp.isoformat(),
      'data_time_ct':stamp.astimezone(CT).isoformat(),
      'market_open_utc':op.isoformat(),
      'market_close_utc':cl.isoformat(),
      'etfs':data,
      'vix':round(vx,3),
      'source':'Yahoo Finance intraday via yfinance; delayed/non-exchange-grade'
    }
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
