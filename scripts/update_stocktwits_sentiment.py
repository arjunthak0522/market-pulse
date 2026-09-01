#!/usr/bin/env python3
import json,os
from datetime import datetime,timezone
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'stocktwits_sentiment.json'
BASE='https://api-gw-prd.stocktwits.com/api-middleware/external/sentiment/v2/{symbol}/detail'
SYMBOLS=['SPY','QQQ']


def previous():
    try:return json.loads(OUT.read_text())
    except:return {'status':'unavailable','symbols':{}}


def parse_detail(payload):
    # Firestream payloads can evolve. Prefer canonical score/label and normalized message-volume fields.
    sentiment=payload.get('sentiment') or payload.get('data',{}).get('sentiment') or {}
    volume=payload.get('message_volume') or payload.get('data',{}).get('message_volume') or payload.get('volume') or {}
    if isinstance(volume,list):
        now=next((x for x in volume if str(x.get('timeframe','')).lower()=='now'),{})
    else:now=volume
    score=sentiment.get('score',sentiment.get('normalized_value'))
    label=sentiment.get('label',sentiment.get('normalized_label'))
    vscore=now.get('score',now.get('normalized_value')) if isinstance(now,dict) else None
    vlabel=now.get('label',now.get('normalized_label')) if isinstance(now,dict) else None
    return {
        'sentiment_score':None if score is None else float(score),
        'sentiment_label':label,
        'message_volume_score':None if vscore is None else float(vscore),
        'message_volume_label':vlabel,
    }


def main():
    user=os.getenv('STOCKTWITS_API_USER')
    password=os.getenv('STOCKTWITS_API_PASSWORD')
    if not user or not password:
        old=previous();old['status']='credentials_required';old['note']='Configure STOCKTWITS_API_USER and STOCKTWITS_API_PASSWORD GitHub Actions secrets for Firestream sentiment.'
        OUT.write_text(json.dumps(old,indent=2)+'\n')
        print('Stocktwits credentials not configured; preserving prior readings.')
        return

    symbols={}
    for symbol in SYMBOLS:
        r=requests.get(BASE.format(symbol=symbol),auth=HTTPBasicAuth(user,password),headers={'Accept':'application/json'},timeout=40)
        r.raise_for_status()
        symbols[symbol]=parse_detail(r.json())

    out={
        'status':'ok',
        'as_of':datetime.now(timezone.utc).isoformat(),
        'source':'Stocktwits Firestream Sentiment V2',
        'symbols':symbols,
        'interpretation':'Sentiment and message volume are crowd-context signals only. They do not override trend, participation, or options-risk evidence.'
    }
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
