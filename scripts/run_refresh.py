#!/usr/bin/env python3
"""Runtime adapter for the seven-signal builder.

Yahoo's v8 chart endpoint is keyless and works in non-browser environments. It
is used only for SPY forward-return history; all signal values keep their own
market-specific sources.
"""
from datetime import datetime, timezone

import pandas as pd

import update_extremes as builder


def yahoo_spy_history():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/SPY"
    params = {
        "period1": 728317800,  # 1993-01-29 UTC
        "period2": int(datetime.now(timezone.utc).timestamp()) + 86400,
        "interval": "1d",
        "events": "div,splits",
        "includeAdjustedClose": "true",
    }
    r = builder.requests.get(url, params=params, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
    }, timeout=45)
    r.raise_for_status()
    payload = r.json()
    result = (payload.get("chart", {}).get("result") or [None])[0]
    if not result:
        raise RuntimeError(f"Yahoo SPY chart unavailable: {payload.get('chart', {}).get('error')}")
    ts = result.get("timestamp") or []
    indicators = result.get("indicators") or {}
    adj = (indicators.get("adjclose") or [{}])[0].get("adjclose")
    close = (indicators.get("quote") or [{}])[0].get("close")
    vals = adj or close or []
    if len(ts) != len(vals) or len(ts) < 1000:
        raise RuntimeError("Yahoo SPY history incomplete")
    s = pd.Series(vals, index=pd.to_datetime(ts, unit="s", utc=True).tz_convert(None), dtype="float64").dropna()
    s.index = s.index.normalize()
    return s[~s.index.duplicated(keep="last")].sort_index()


if __name__ == "__main__":
    builder.spy_history = yahoo_spy_history
    builder.main()
