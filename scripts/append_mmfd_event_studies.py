#!/usr/bin/env python3
"""Append one-week participation ($MMFD-equivalent) studies to event_studies.json.

Market Pulse's `above_5d` breadth field is the percentage of S&P 500 stocks
above their 5-day moving average - the same concept represented by Barchart's
$MMFD breadth index. This module intentionally uses only Market Pulse's
prospectively recorded breadth history. It does not backfill today's S&P 500
constituents into the past and does not claim a longer breadth history than we
actually possess.
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


def crossing_below(s, level):
    return s.lt(level) & s.shift(1).ge(level)


def recovery_above_after(s, low, recovery):
    # Fires once when breadth recovers above `recovery` after having reached
    # the specified washout threshold during the prior 10 trading sessions.
    prior_washout = s.shift(1).rolling(10, min_periods=1).min().lt(low)
    return s.gt(recovery) & s.shift(1).le(recovery) & prior_washout


def download(symbol, start, end):
    df = yf.download(symbol, start=start, end=end, interval="1d", auto_adjust=True,
                     progress=False, threads=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if df.empty:
        raise RuntimeError(f"No data for {symbol}")
    return df["Close"].astype(float)


def main():
    payload = json.loads(OUT.read_text())
    hist = json.loads(HISTORY.read_text())
    rows = hist.get("breadth", [])
    if len(rows) < 20:
        print("Breadth history too short - no MMFD studies appended")
        return

    b = pd.DataFrame(rows)
    b["date"] = pd.to_datetime(b["date"])
    b = b.set_index("date").sort_index()
    b["above_5d"] = pd.to_numeric(b["above_5d"], errors="coerce")
    b = b.dropna(subset=["above_5d"])
    start = b.index.min().strftime("%Y-%m-%d")
    end = (b.index.max() + pd.Timedelta(days=5)).strftime("%Y-%m-%d")

    rules = [
        ("mmfd_cross_below_20", "One-week participation falls below 20%", "One-week participation crosses from >=20% to <20%.", crossing_below(b.above_5d, 20), 88),
        ("mmfd_cross_below_15", "One-week participation falls below 15%", "One-week participation crosses from >=15% to <15%.", crossing_below(b.above_5d, 15), 94),
        ("mmfd_cross_below_10", "One-week participation falls below 10%", "One-week participation crosses from >=10% to <10%.", crossing_below(b.above_5d, 10), 98),
        ("mmfd_recover_20_after_15", "One-week participation recovers above 20% after washout", "One-week participation crosses above 20% after falling below 15% during the prior 10 trading sessions.", recovery_above_after(b.above_5d, 15, 20), 99),
        ("mmfd_recover_50_after_20", "One-week participation recovers above 50% after broad weakness", "One-week participation crosses above 50% after falling below 20% during the prior 10 trading sessions.", recovery_above_after(b.above_5d, 20, 50), 96),
    ]

    existing = {s.get("study_id") for s in payload.get("studies", [])}
    current = payload.setdefault("current_events", [])
    studies = payload.setdefault("studies", [])

    for symbol in ("SPY", "QQQ"):
        close = download(symbol, start, end)
        aligned = pd.DataFrame({"breadth": b.above_5d}).join(close.rename("close"), how="inner").dropna()
        if len(aligned) < 20:
            continue
        for signal_id, title, rule, raw_mask, priority in rules:
            mask = raw_mask.reindex(aligned.index, fill_value=False)
            positions = np.flatnonzero(mask.to_numpy(dtype=bool)).tolist()
            if not positions:
                continue
            study_id = f"{symbol.lower()}:{signal_id}"
            if study_id in existing:
                continue
            horizons = {}
            for h in HORIZONS:
                sig_vals = [aligned.close.iloc[p+h] / aligned.close.iloc[p] - 1 for p in positions if p+h < len(aligned)]
                base_vals = [aligned.close.iloc[p+h] / aligned.close.iloc[p] - 1 for p in range(0, len(aligned)-h)]
                ss, bs = stats(sig_vals), stats(base_vals)
                horizons[str(h)] = {
                    "signal": ss,
                    "baseline": bs,
                    "edge": {
                        "median_excess": None if ss.get("median") is None or bs.get("median") is None else round(ss["median"]-bs["median"], 4),
                        "positive_rate_advantage_pp": None if ss.get("positive_rate") is None or bs.get("positive_rate") is None else round(ss["positive_rate"]-bs["positive_rate"], 1),
                    },
                }
            n21 = horizons["21"]["signal"].get("n", 0)
            study = {
                "study_id": study_id,
                "signal_id": signal_id,
                "symbol": symbol,
                "title": f"{symbol} - {title}",
                "category": "One-week participation",
                "definition": {
                    "rule": rule,
                    "event_logic": "Transition event only - repeated days below/above a threshold are not counted as new signals.",
                    "cooldown_sessions": 0,
                    "condition_logic": "SINGLE",
                    "conditions": [signal_id],
                    "compound_ready": True,
                },
                "historical_sample": len(positions),
                "complete_21d_sample": n21,
                "first_event": str(aligned.index[positions[0]].date()),
                "last_event": str(aligned.index[positions[-1]].date()),
                "evidence": evidence(n21),
                "horizons": horizons,
                "regime_splits": [],
                "recent_events": [{"event_date": str(aligned.index[p].date())} for p in positions[-12:]],
                "diagnostics": ["Breadth history is limited to Market Pulse's prospectively recorded S&P 500 universe; no constituent-history backfill is used."],
            }
            h5 = horizons["5"]; ss=h5["signal"]; bs=h5["baseline"]; edge=h5["edge"]
            if ss.get("n",0) < 10:
                study["commentary"] = f"Only {ss.get('n',0)} complete 5-day examples are available in the verified breadth history, so this is early evidence only. Market Pulse will strengthen this study automatically as more exact observations accumulate."
            else:
                study["commentary"] = f"Across {ss['n']} verified examples, the typical 5-day {symbol} return was {ss['median']:+.2f}% and {ss['positive_rate']:.0f}% finished higher, versus {bs['positive_rate']:.0f}% during normal periods. The median difference versus normal was {edge['median_excess']:+.2f}%."
            studies.append(study)
            if bool(mask.iloc[-1]):
                current.append({"study_id":study_id,"signal_id":signal_id,"symbol":symbol,"title":study["title"],"event_date":str(aligned.index[-1].date()),"rule":rule,"priority":priority,"historical_sample":len(positions),"evidence":study["evidence"]})

    payload.setdefault("methodology", {})["one_week_participation"] = "Market Pulse above_5d = percent of the tracked S&P 500 universe above its 5-day moving average, equivalent in concept to $MMFD. Breadth event studies use only prospectively recorded Market Pulse history and are explicitly labeled when sample depth is limited."
    payload["studies"].sort(key=lambda x:(x.get("symbol",""),x.get("category",""),x.get("title","")))
    payload["current_events"].sort(key=lambda x:(-x.get("priority",0),x.get("symbol",""),x.get("signal_id","")))
    OUT.write_text(json.dumps(payload, indent=2, allow_nan=False)+"\n")
    print("Appended verified one-week participation studies")

if __name__ == "__main__":
    main()
