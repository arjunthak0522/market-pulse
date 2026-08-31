#!/usr/bin/env python3
"""Append recorded-history breadth-momentum event studies.

Signals use only Market Pulse's recorded S&P 500 advance/decline history.
The breadth-momentum oscillator is McClellan-style, normalized to the tracked
S&P 500 universe, and is not labeled as the NYSE McClellan Oscillator.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data" / "history.json"
OUT = ROOT / "data" / "event_studies.json"
HORIZONS = (1, 2, 3, 5, 10, 21, 63)


def evidence(n):
    if n < 10: return "Very limited"
    if n < 20: return "Limited"
    if n < 50: return "Moderate"
    if n < 100: return "Strong"
    return "High sample depth"


def stats(values):
    a = np.asarray([x for x in values if x is not None and np.isfinite(x)], dtype=float)
    if not len(a): return {"n": 0}
    return {
        "n": int(len(a)), "average": round(100*a.mean(),4), "median": round(100*np.median(a),4),
        "positive_rate": round(100*np.mean(a>0),1), "negative_rate": round(100*np.mean(a<0),1),
        "best": round(100*a.max(),4), "worst": round(100*a.min(),4),
        "p25": round(100*np.percentile(a,25),4), "p75": round(100*np.percentile(a,75),4),
    }


def frame():
    hist = json.loads(HISTORY.read_text())
    df = pd.DataFrame(hist.get("breadth", []))
    if df.empty: return df
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    for c in ("advancers","decliners","above_5d"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    active=(df.advancers+df.decliners).replace(0,np.nan)
    net=100*(df.advancers-df.decliners)/active
    df["osc"]=net.ewm(span=19,adjust=False).mean()-net.ewm(span=39,adjust=False).mean()
    def last_rank(x):
        s=pd.Series(x);return 100*s.rank(pct=True).iloc[-1]
    df["pct"]=df.osc.rolling(63,min_periods=40).apply(last_rank,raw=False)
    return df.dropna(subset=["above_5d","osc"])


def download(symbol,start,end):
    d=yf.download(symbol,start=start,end=end,interval="1d",auto_adjust=True,progress=False,threads=False)
    if isinstance(d.columns,pd.MultiIndex): d.columns=d.columns.get_level_values(0)
    if d.empty: raise RuntimeError(f"No data for {symbol}")
    return d["Close"].astype(float)


def main():
    payload=json.loads(OUT.read_text()); b=frame()
    if len(b)<45:
        print("Breadth history too short - no breadth-cycle studies appended"); return
    # Point-in-time percentile events. Each percentile uses only its trailing 63-session window.
    bottom_decile=(b.pct<=10)&(b.pct.shift(1)>10)
    recover20=(b.pct>20)&(b.pct.shift(1)<=20)&(b.pct.shift(1).rolling(10,min_periods=1).min()<=10)
    osc_zero=(b.osc>0)&(b.osc.shift(1)<=0)&(b.above_5d>50)&(b.above_5d.shift(1).rolling(10,min_periods=1).min()<20)
    rules=[
        ("breadth_momentum_bottom_decile","Breadth momentum enters bottom decile","McClellan-style S&P 500 breadth momentum enters the bottom 10% of its trailing 63-session range.",bottom_decile,92),
        ("breadth_momentum_recover_20","Breadth momentum begins recovering from an extreme","Breadth-momentum percentile crosses above 20 after reaching the bottom decile during the prior 10 sessions.",recover20,98),
        ("breadth_recovery_confirmed","Breadth recovery confirmation","Breadth momentum crosses above neutral while one-week participation is above 50%, after one-week participation fell below 20% during the prior 10 sessions.",osc_zero,100),
    ]
    studies=payload.setdefault("studies",[]); current=payload.setdefault("current_events",[]); existing={s.get("study_id") for s in studies}
    start=b.index.min().strftime("%Y-%m-%d"); end=(b.index.max()+pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    for symbol in ("SPY","QQQ"):
        close=download(symbol,start,end)
        aligned=pd.DataFrame({"breadth":b.above_5d,"osc":b.osc,"pct":b.pct}).join(close.rename("close"),how="inner").dropna(subset=["close","osc"])
        for signal_id,title,rule,raw_mask,priority in rules:
            mask=raw_mask.reindex(aligned.index,fill_value=False)
            pos=np.flatnonzero(mask.to_numpy(dtype=bool)).tolist()
            if not pos: continue
            sid=f"{symbol.lower()}:{signal_id}"
            if sid in existing: continue
            horizons={}
            for h in HORIZONS:
                sig=[aligned.close.iloc[p+h]/aligned.close.iloc[p]-1 for p in pos if p+h<len(aligned)]
                base=[aligned.close.iloc[p+h]/aligned.close.iloc[p]-1 for p in range(len(aligned)-h)]
                ss,bs=stats(sig),stats(base)
                horizons[str(h)]={"signal":ss,"baseline":bs,"edge":{"median_excess":None if ss.get("median") is None or bs.get("median") is None else round(ss["median"]-bs["median"],4),"positive_rate_advantage_pp":None if ss.get("positive_rate") is None or bs.get("positive_rate") is None else round(ss["positive_rate"]-bs["positive_rate"],1)}}
            n21=horizons["21"]["signal"].get("n",0)
            study={
                "study_id":sid,"signal_id":signal_id,"symbol":symbol,"title":f"{symbol} - {title}","category":"Breadth cycle",
                "definition":{"rule":rule,"event_logic":"Transition event only; repeated days in the same state are not new signals.","cooldown_sessions":0,"condition_logic":"SINGLE","conditions":[signal_id],"compound_ready":True},
                "historical_sample":len(pos),"complete_21d_sample":n21,"first_event":str(aligned.index[pos[0]].date()),"last_event":str(aligned.index[pos[-1]].date()),"evidence":evidence(n21),"horizons":horizons,"regime_splits":[],"recent_events":[{"event_date":str(aligned.index[p].date())} for p in pos[-12:]],
                "diagnostics":["Uses only recorded S&P 500 advance/decline observations. Breadth momentum is McClellan-style and normalized to this universe; it is not the NYSE McClellan Oscillator."],
            }
            n5=horizons["5"]["signal"].get("n",0)
            if n5<10: study["commentary"]=f"Only {n5} complete 5-day examples are available in the verified breadth history, so this is early evidence only."
            else:
                s=horizons["5"]["signal"]; study["commentary"]=f"Across {s['n']} verified examples, the typical 5-day {symbol} return was {s['median']:+.2f}% and {s['positive_rate']:.0f}% finished higher."
            studies.append(study)
            if bool(mask.iloc[-1]): current.append({"study_id":sid,"signal_id":signal_id,"symbol":symbol,"title":study["title"],"event_date":str(aligned.index[-1].date()),"rule":rule,"priority":priority,"historical_sample":len(pos),"evidence":study["evidence"]})
    payload.setdefault("methodology",{})["breadth_cycle"]="McClellan-style breadth momentum uses 19- and 39-session EMAs of normalized net advances from Market Pulse's recorded S&P 500 advance/decline universe. Percentile signals use trailing windows only."
    studies.sort(key=lambda x:(x.get("symbol",""),x.get("category",""),x.get("title","")))
    current.sort(key=lambda x:(-x.get("priority",0),x.get("symbol",""),x.get("signal_id","")))
    OUT.write_text(json.dumps(payload,indent=2,allow_nan=False)+"\n")
    print("Appended breadth-cycle studies")

if __name__=="__main__": main()
