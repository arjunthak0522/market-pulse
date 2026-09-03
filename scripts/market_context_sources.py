#!/usr/bin/env python3
"""Same-session free market context for Leadership and Technical Extremes.

Uses adjusted daily ETF prices through the repo's existing yfinance dependency. The
output is a small cache consumed only by Event Intelligence. A temporary Yahoo failure
retains a recent last-known-good cache with LOW confidence and a hard 4-day TTL.
"""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "event_market_context.json"
SECTORS = {
    "XLB": "Materials",
    "XLC": "Communication Services",
    "XLE": "Energy",
    "XLF": "Financials",
    "XLI": "Industrials",
    "XLK": "Technology",
    "XLP": "Consumer Staples",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
    "XLV": "Health Care",
    "XLY": "Consumer Discretionary",
}
TICKERS = ["SPY", "QQQ", *SECTORS]
TTL_DAYS = 4


def _read_previous() -> dict:
    try:
        obj = json.loads(OUT.read_text())
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _download() -> pd.DataFrame:
    raw = yf.download(
        TICKERS,
        period="1y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
        group_by="column",
    )
    if raw.empty:
        raise RuntimeError("Yahoo/yfinance returned no ETF history")
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"].copy()
    else:
        close = pd.DataFrame({TICKERS[0]: raw["Close"]})
    close.index = pd.to_datetime(close.index).tz_localize(None)
    close = close.sort_index().dropna(how="all")
    missing = [t for t in TICKERS if t not in close.columns]
    if missing:
        raise RuntimeError(f"ETF history missing tickers: {missing}")
    return close


def _rsi(series: pd.Series, n: int = 14) -> float | None:
    s = series.dropna()
    if len(s) < n + 2:
        return None
    delta = s.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    rs = gain / loss.replace(0, np.nan)
    value = 100 - 100 / (1 + rs)
    return None if pd.isna(value.iloc[-1]) else float(value.iloc[-1])


def _technical(series: pd.Series) -> dict:
    s = series.dropna()
    if len(s) < 30:
        raise RuntimeError("ETF history too short for technical context")
    last = float(s.iloc[-1])
    high14 = float(s.tail(14).max())
    low14 = float(s.tail(14).min())
    wr = -50.0 if high14 == low14 else -100 * (high14 - last) / (high14 - low14)
    ma20 = float(s.tail(20).mean())
    sd20 = float(s.tail(20).std(ddof=0))
    upper, lower = ma20 + 2 * sd20, ma20 - 2 * sd20
    bb = 0.5 if upper == lower else (last - lower) / (upper - lower)
    return {
        "price": round(last, 3),
        "rsi14": None if _rsi(s) is None else round(_rsi(s), 3),
        "williams_r14": round(wr, 3),
        "bollinger_pct_b": round(float(bb), 4),
        "distance_ma20": round((last / ma20 - 1) * 100, 3),
    }


def _ret(series: pd.Series, sessions: int) -> float:
    s = series.dropna()
    if len(s) <= sessions:
        raise RuntimeError("ETF history too short for relative return")
    return (float(s.iloc[-1]) / float(s.iloc[-1-sessions]) - 1) * 100


def build() -> dict:
    close = _download()
    latest_dates = [close[t].dropna().index[-1] for t in TICKERS]
    market_date = min(latest_dates).date().isoformat()
    spy5, spy20 = _ret(close["SPY"], 5), _ret(close["SPY"], 20)

    leadership = []
    for ticker, name in SECTORS.items():
        r5, r20 = _ret(close[ticker], 5), _ret(close[ticker], 20)
        rel5, rel20 = r5 - spy5, r20 - spy20
        acceleration = rel5 - rel20
        if rel20 >= 1.0 and rel5 >= 0:
            status = "Leader"
        elif rel20 <= -1.0 and rel5 <= 0:
            status = "Lagging"
        else:
            status = "Neutral"
        leadership.append({
            "ticker": ticker,
            "name": name,
            "relative_5d": round(rel5, 3),
            "relative_20d": round(rel20, 3),
            "relative_acceleration": round(acceleration, 3),
            "return_5d": round(r5, 3),
            "status": status,
        })
    leadership.sort(key=lambda x: (x["relative_20d"], x["relative_5d"]), reverse=True)

    context = {
        "market_date": market_date,
        "sector_leadership": leadership,
        "relative_strength": {"qqq_vs_spy_20d": round(_ret(close["QQQ"], 20) - spy20, 3)},
        "etfs": {
            "SPY": {**_technical(close["SPY"]), "market_date": market_date},
            "QQQ": {**_technical(close["QQQ"]), "market_date": market_date},
        },
        "component_status": {
            "sector_leadership": {"as_of": market_date, "source": "Adjusted sector ETF closes via Yahoo/yfinance"},
            "SPY": {"as_of": market_date, "source": "Adjusted SPY closes via Yahoo/yfinance"},
            "QQQ": {"as_of": market_date, "source": "Adjusted QQQ closes via Yahoo/yfinance"},
        },
    }
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "freshness": "current_provider",
        "confidence": "MODERATE",
        "source": "Yahoo Finance adjusted ETF history via yfinance",
        "context": context,
        "error": None,
    }


def _fallback(previous: dict, error: str) -> dict | None:
    ctx = previous.get("context") if isinstance(previous, dict) else None
    if not isinstance(ctx, dict) or not ctx.get("market_date"):
        return None
    try:
        age = max(0, (date.today() - date.fromisoformat(str(ctx["market_date"])[:10])).days)
    except Exception:
        return None
    if age > TTL_DAYS:
        return None
    out = deepcopy(previous)
    out["generated_at"] = datetime.now(timezone.utc).isoformat()
    out["freshness"] = "stale_fallback"
    out["confidence"] = "LOW"
    out["stale_age_days"] = age
    out["stale_ttl_days"] = TTL_DAYS
    out["error"] = error
    return out


def main() -> dict:
    previous = _read_previous()
    try:
        out = build()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        out = _fallback(previous, error) or {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "freshness": "unavailable",
            "confidence": "LOW",
            "source": "Yahoo Finance adjusted ETF history via yfinance",
            "context": {},
            "error": error,
        }
    OUT.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    return out


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
