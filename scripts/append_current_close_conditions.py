#!/usr/bin/env python3
"""Append historical studies for conditions active at Market Pulse's confirmed close.

These are deliberately different from crossing/transition signals. They answer:
"When the market CLOSED with a setup like today's confirmed close, what happened next?"
Price/VIX conditions use long ETF/VIX history. Breadth conditions use only Market
Pulse's prospectively recorded breadth history and disclose that limitation.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "event_studies.json"
CONTEXT = ROOT / "data" / "market_context.json"
HISTORY = ROOT / "data" / "history.json"
HORIZONS = (1, 5, 10, 21)
START = "1999-01-01"
PREFIX = "current_close_"


def safe(v):
    try:
        x = float(v)
        return x if np.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def stats(values):
    a = np.asarray([x for x in values if x is not None and np.isfinite(x)], dtype=float)
    if not len(a):
        return {"n": 0}
    return {
        "n": int(len(a)),
        "average": round(100 * a.mean(), 4),
        "median": round(100 * np.median(a), 4),
        "positive_rate": round(100 * np.mean(a > 0), 1),
        "negative_rate": round(100 * np.mean(a < 0), 1),
        "best": round(100 * a.max(), 4),
        "worst": round(100 * a.min(), 4),
        "p25": round(100 * np.percentile(a, 25), 4),
        "p75": round(100 * np.percentile(a, 75), 4),
    }


def evidence(n):
    if n < 10: return "Very limited"
    if n < 20: return "Limited"
    if n < 50: return "Moderate"
    if n < 100: return "Strong"
    return "High sample depth"


def download(symbol, target_date):
    end = (pd.Timestamp(target_date) + pd.Timedelta(days=5)).strftime("%Y-%m-%d")
    df = yf.download(symbol, start=START, end=end, interval="1d", auto_adjust=True,
                     progress=False, threads=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if df.empty:
        raise RuntimeError(f"No data for {symbol}")
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df.loc[df.index <= pd.Timestamp(target_date)].copy()


def prepare_price(symbol, target_date, vix):
    raw = download(symbol, target_date)
    df = pd.DataFrame(index=raw.index)
    df["close"] = raw["Close"].astype(float)
    df["high"] = raw["High"].astype(float)
    df["low"] = raw["Low"].astype(float)
    for p in (20, 50, 200):
        df[f"ma{p}"] = df.close.rolling(p).mean()
        df[f"dist{p}"] = 100 * (df.close / df[f"ma{p}"] - 1)
    df["vix"] = vix.reindex(df.index).ffill()
    return df.dropna(subset=["ma200"])


def summarize(df, mask):
    positions = np.flatnonzero(mask.fillna(False).to_numpy(dtype=bool)).tolist()
    horizons = {}
    for h in HORIZONS:
        sig = [df.close.iloc[p+h] / df.close.iloc[p] - 1 for p in positions if p+h < len(df)]
        base = [df.close.iloc[p+h] / df.close.iloc[p] - 1 for p in range(0, len(df)-h)]
        ss, bs = stats(sig), stats(base)
        item = {
            "signal": ss,
            "baseline": bs,
            "edge": {
                "median_excess": None if ss.get("median") is None or bs.get("median") is None else round(ss["median"] - bs["median"], 4),
                "positive_rate_advantage_pp": None if ss.get("positive_rate") is None or bs.get("positive_rate") is None else round(ss["positive_rate"] - bs["positive_rate"], 1),
            },
        }
        if h in (10, 21):
            maes, mfes = [], []
            for p in positions:
                if p+h >= len(df):
                    continue
                base_px = float(df.close.iloc[p])
                w = df.iloc[p+1:p+h+1]
                maes.append(float((w.low / base_px - 1).min()))
                mfes.append(float((w.high / base_px - 1).max()))
            item["path"] = {
                "n": len(maes),
                "median_max_drawdown": None if not maes else round(100 * float(np.median(maes)), 4),
                "median_max_rally": None if not mfes else round(100 * float(np.median(mfes)), 4),
                "maximum_adverse_excursion": None if not maes else round(100 * float(np.min(maes)), 4),
                "maximum_favorable_excursion": None if not mfes else round(100 * float(np.max(mfes)), 4),
                "thresholds": {},
            }
        horizons[str(h)] = item
    return positions, horizons


def study(symbol, signal_id, title, rule, df, mask, target_date, priority, diagnostics=None):
    positions, horizons = summarize(df, mask)
    if not positions:
        return None, None
    n21 = horizons["21"]["signal"].get("n", 0)
    s = {
        "study_id": f"{symbol.lower()}:{PREFIX}{signal_id}",
        "signal_id": f"{PREFIX}{signal_id}",
        "symbol": symbol,
        "title": title,
        "category": "Current close setup",
        "event_kind": "close_condition",
        "definition": {
            "rule": rule,
            "event_logic": "Condition-at-close study. Each eligible historical close matching the full rule is included; overlapping observations can occur.",
            "cooldown_sessions": 0,
            "condition_logic": "ALL",
            "conditions": [signal_id],
            "compound_ready": True,
        },
        "historical_sample": len(positions),
        "complete_21d_sample": n21,
        "first_event": str(df.index[positions[0]].date()),
        "last_event": str(df.index[positions[-1]].date()),
        "evidence": evidence(n21),
        "horizons": horizons,
        "regime_splits": [],
        "recent_events": [{"event_date": str(df.index[p].date())} for p in positions[-12:]],
        "diagnostics": diagnostics or ["Condition-at-close studies can contain overlapping historical windows; use them as context, not independent trials."],
    }
    active = bool(mask.reindex(df.index, fill_value=False).iloc[-1]) and str(df.index[-1].date()) == target_date
    event = None
    if active:
        event = {
            "study_id": s["study_id"],
            "signal_id": s["signal_id"],
            "symbol": symbol,
            "title": title,
            "event_date": target_date,
            "rule": rule,
            "priority": priority,
            "historical_sample": len(positions),
            "evidence": s["evidence"],
            "event_kind": "close_condition",
        }
    return s, event


def main():
    payload = json.loads(OUT.read_text())
    context = json.loads(CONTEXT.read_text())
    target_date = str(context.get("market_date") or "")
    if not target_date:
        raise RuntimeError("market_context.json has no confirmed market_date")

    payload["studies"] = [s for s in payload.get("studies", []) if PREFIX not in s.get("signal_id", "")]
    payload["current_events"] = [e for e in payload.get("current_events", []) if PREFIX not in e.get("signal_id", "")]

    vix_raw = download("^VIX", target_date)
    vix = vix_raw["Close"].astype(float)
    spy = prepare_price("SPY", target_date, vix)
    qqq = prepare_price("QQQ", target_date, vix)

    specs = [
        ("SPY", "intact_trend_near_20d", "SPY intact uptrend near its 20-day trend",
         "SPY closes above its 50-day and 200-day averages and within 1% of its 20-day average.",
         spy, (spy.close > spy.ma50) & (spy.close > spy.ma200) & spy.dist20.abs().le(1.0), 91),
        ("QQQ", "soft_20d_intact_long_term", "QQQ short-term softness inside an intact uptrend",
         "QQQ closes above its 50-day and 200-day averages while at or below 0.5% above its 20-day average.",
         qqq, (qqq.close > qqq.ma50) & (qqq.close > qqq.ma200) & qqq.dist20.le(0.5), 93),
        ("SPY", "calm_pullback_vix_below_15", "Low fear while SPY sits near short-term trend",
         "VIX closes below 15 while SPY remains above its 200-day average and no more than 1% above its 20-day average.",
         spy, spy.vix.lt(15) & (spy.close > spy.ma200) & spy.dist20.le(1.0), 89),
    ]

    additions, events = [], []
    for args in specs:
        s, e = study(*args, target_date)
        if s: additions.append(s)
        if e: events.append(e)

    hist = json.loads(HISTORY.read_text())
    b = pd.DataFrame(hist.get("breadth", []))
    if not b.empty:
        b["date"] = pd.to_datetime(b["date"])
        b = b.set_index("date").sort_index()
        for col in ("above_5d", "above_50d", "above_200d"):
            b[col] = pd.to_numeric(b[col], errors="coerce")
        b = b.loc[b.index <= pd.Timestamp(target_date)]
        px = download("SPY", target_date)
        bdf = b.join(pd.DataFrame({"close": px["Close"], "high": px["High"], "low": px["Low"]}), how="inner").dropna(subset=["above_5d", "above_50d", "above_200d", "close"])
        breadth_diag = ["Breadth studies use only Market Pulse's prospectively recorded S&P 500 breadth history; sample depth is limited and grows daily.", "Condition-at-close studies can contain overlapping historical windows; use them as context, not independent trials."]
        breadth_specs = [
            ("short_weak_long_healthy", "Short-term participation weak while long-term breadth stays healthy",
             "5-day breadth is below 35% while 200-day breadth is at least 60%.",
             bdf.above_5d.lt(35) & bdf.above_200d.ge(60), 97),
            ("intermediate_neutral_long_healthy", "Intermediate breadth neutral while long-term participation stays healthy",
             "50-day breadth is between 45% and 60% while 200-day breadth is at least 60%.",
             bdf.above_50d.between(45, 60) & bdf.above_200d.ge(60), 90),
        ]
        for signal_id, title, rule, mask, priority in breadth_specs:
            s, e = study("SPY", signal_id, title, rule, bdf, mask, target_date, priority, breadth_diag)
            if s: additions.append(s)
            if e: events.append(e)

    payload.setdefault("methodology", {})["current_close_conditions"] = "Current-close studies are anchored to market_context.market_date, the dashboard's latest confirmed close. Price/VIX studies use historical SPY/QQQ/VIX data. Breadth studies use only prospectively recorded Market Pulse breadth history."
    payload["studies"].extend(additions)
    payload["current_events"].extend(events)
    payload["studies"].sort(key=lambda x: (x.get("symbol", ""), x.get("category", ""), x.get("title", "")))
    payload["current_events"].sort(key=lambda x: (-x.get("priority", 0), x.get("symbol", ""), x.get("signal_id", "")))
    OUT.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    print(f"Appended {len(additions)} current-close studies; {len(events)} are active for {target_date}")


if __name__ == "__main__":
    main()
