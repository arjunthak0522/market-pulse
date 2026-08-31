#!/usr/bin/env python3
"""Build tactical breadth-cycle and sector-leadership context.

Breadth momentum is McClellan-style, but intentionally normalized to Market
Pulse's recorded S&P 500 advance/decline universe. It is not presented as the
NYSE McClellan Oscillator. The oscillator uses the difference between 19- and
39-session EMAs of normalized net advances:

    100 * (advancers - decliners) / (advancers + decliners)

Only recorded breadth history is used, so past breadth is not reconstructed
with today's constituents.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data" / "history.json"
MARKET = ROOT / "data" / "market_context.json"

SECTORS = {
    "XLK": "Technology",
    "XLC": "Communication Services",
    "XLY": "Consumer Discretionary",
    "XLF": "Financials",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLE": "Energy",
    "XLV": "Health Care",
    "XLP": "Consumer Staples",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
}


def safe_float(v):
    try:
        x = float(v)
        return x if np.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def breadth_frame(history: dict) -> pd.DataFrame:
    rows = history.get("breadth", [])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if "date" not in df:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).set_index("date").sort_index()
    for c in ("advancers", "decliners", "above_5d", "above_20d", "above_50d", "above_200d"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "advancers" not in df or "decliners" not in df:
        return pd.DataFrame()
    active = (df["advancers"] + df["decliners"]).replace(0, np.nan)
    df["normalized_net_advances"] = 100 * (df["advancers"] - df["decliners"]) / active
    df["breadth_momentum"] = (
        df["normalized_net_advances"].ewm(span=19, adjust=False).mean()
        - df["normalized_net_advances"].ewm(span=39, adjust=False).mean()
    )
    df["breadth_momentum_change"] = df["breadth_momentum"].diff()
    # Rolling percentile uses only the contemporaneous trailing window.
    def last_rank(x):
        s = pd.Series(x)
        return 100 * s.rank(pct=True).iloc[-1]
    df["breadth_momentum_percentile"] = df["breadth_momentum"].rolling(63, min_periods=40).apply(last_rank, raw=False)
    return df


def cycle_state(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"state": "Unavailable", "read": "Breadth-cycle history is unavailable."}
    row = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else row
    b5 = safe_float(row.get("above_5d"))
    osc = safe_float(row.get("breadth_momentum"))
    change = safe_float(row.get("breadth_momentum_change"))
    pct = safe_float(row.get("breadth_momentum_percentile"))
    prior10 = df.tail(10)
    min_b5 = safe_float(prior10["above_5d"].min()) if "above_5d" in prior10 else None
    min_pct = safe_float(prior10["breadth_momentum_percentile"].min()) if "breadth_momentum_percentile" in prior10 else None
    prev_b5 = safe_float(prev.get("above_5d"))
    recovering = change is not None and change > 0

    if min_b5 is not None and min_b5 < 20 and b5 is not None and b5 >= 50 and osc is not None and osc > 0:
        state, read = "Breadth recovery", "Participation has recovered broadly after a washout and breadth momentum is back above neutral."
    elif min_pct is not None and min_pct <= 10 and recovering and b5 is not None and prev_b5 is not None and b5 > prev_b5:
        state, read = "Stabilizing", "Breadth momentum is turning higher after an extreme while one-week participation is also improving."
    elif b5 is not None and b5 < 15 and pct is not None and pct <= 15:
        state, read = "Washout", "One-week participation and breadth momentum are both in extreme territory."
    elif (b5 is not None and b5 < 30) or (pct is not None and pct <= 25):
        state, read = "Approaching washout", "Breadth is deteriorating toward an extreme, but a recovery signal has not appeared yet."
    elif change is not None and change < 0 and b5 is not None and b5 < 50:
        state, read = "Deteriorating", "Short-term participation is soft and breadth momentum is still weakening."
    else:
        state, read = "Healthy / neutral", "Breadth is not showing a confirmed washout or recovery transition."

    direction = "Improving" if change is not None and change > 0.35 else "Deteriorating" if change is not None and change < -0.35 else "Stable"
    return {
        "state": state,
        "read": read,
        "value": None if osc is None else round(osc, 3),
        "change": None if change is None else round(change, 3),
        "percentile_63d": None if pct is None else round(pct, 1),
        "direction": direction,
        "method": "19-session EMA minus 39-session EMA of normalized S&P 500 net advances",
        "technical_name": "McClellan-style Breadth Momentum",
        "universe_note": "Uses Market Pulse's recorded S&P 500 advance/decline universe; it is not the NYSE McClellan Oscillator.",
    }


def sector_leadership() -> list[dict]:
    tickers = ["SPY", *SECTORS.keys()]
    raw = yf.download(tickers, period="6mo", interval="1d", auto_adjust=True,
                      progress=False, threads=True, group_by="ticker")

    def close(sym):
        if isinstance(raw.columns, pd.MultiIndex):
            return raw[sym]["Close"].dropna().astype(float)
        return raw["Close"].dropna().astype(float)

    spy = close("SPY")
    out = []
    for ticker, name in SECTORS.items():
        try:
            s = close(ticker)
            idx = spy.index.intersection(s.index)
            if len(idx) < 25:
                continue
            sp = spy.reindex(idx)
            sec = s.reindex(idx)
            rel = sec / sp
            rel5 = (rel.iloc[-1] / rel.iloc[-6] - 1) * 100
            rel20 = (rel.iloc[-1] / rel.iloc[-21] - 1) * 100
            prev_rel5 = (rel.iloc[-6] / rel.iloc[-11] - 1) * 100 if len(rel) >= 11 else np.nan
            abs5 = (sec.iloc[-1] / sec.iloc[-6] - 1) * 100
            accel = rel5 - prev_rel5 if np.isfinite(prev_rel5) else np.nan
            if rel20 > 1 and rel5 > 0:
                status = "Leader"
            elif rel5 > 0.4 and np.isfinite(accel) and accel > 0.5 and rel20 > -1:
                status = "Emerging leader"
            elif rel5 > 0 and np.isfinite(accel) and accel > 0:
                status = "Improving"
            elif rel20 < -1 and rel5 < 0:
                status = "Lagging"
            else:
                status = "Neutral"
            out.append({
                "ticker": ticker,
                "name": name,
                "relative_5d": round(float(rel5), 3),
                "relative_20d": round(float(rel20), 3),
                "relative_acceleration": None if not np.isfinite(accel) else round(float(accel), 3),
                "return_5d": round(float(abs5), 3),
                "status": status,
            })
        except Exception as exc:
            print("WARN sector", ticker, exc)
    out.sort(key=lambda x: (x["status"] in ("Leader", "Emerging leader", "Improving"), x["relative_5d"], x["relative_20d"]), reverse=True)
    return out


def main():
    history = json.loads(HISTORY.read_text())
    market = json.loads(MARKET.read_text())
    df = breadth_frame(history)
    cycle = cycle_state(df)

    # Persist the derived oscillator onto the recorded breadth rows. These are
    # deterministic transforms of already-recorded observations, not a rebuild.
    if not df.empty:
        derived = {}
        for dt, row in df.iterrows():
            derived[str(dt.date())] = {
                "normalized_net_advances": safe_float(row.get("normalized_net_advances")),
                "breadth_momentum": safe_float(row.get("breadth_momentum")),
                "breadth_momentum_percentile": safe_float(row.get("breadth_momentum_percentile")),
            }
        for rec in history.get("breadth", []):
            d = derived.get(str(rec.get("date")))
            if not d:
                continue
            for key, value in d.items():
                rec[key] = None if value is None else round(value, 3)

    try:
        sectors = sector_leadership()
    except Exception as exc:
        print("WARN sector leadership", exc)
        sectors = market.get("sector_leadership", [])

    market["breadth_cycle"] = cycle
    market["sector_leadership"] = sectors
    market.setdefault("component_status", {})["breadth_cycle"] = {
        "as_of": market.get("market_date"),
        "source": "Derived from recorded S&P 500 advance/decline history",
    }
    market.setdefault("component_status", {})["sector_leadership"] = {
        "as_of": market.get("market_date"),
        "source": "Sector SPDR adjusted closes via Yahoo Finance",
    }
    HISTORY.write_text(json.dumps(history, indent=2, allow_nan=False) + "\n")
    MARKET.write_text(json.dumps(market, indent=2, allow_nan=False) + "\n")
    print("breadth_cycle", cycle.get("state"), "sectors", len(sectors))


if __name__ == "__main__":
    main()
