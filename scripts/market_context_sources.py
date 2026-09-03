#!/usr/bin/env python3
"""Completed-session free market context for Leadership and Technical Extremes.

Uses adjusted daily ETF prices through the repo's existing yfinance dependency. All
calculations are anchored to the exact completed session in data/signal_data.json, so
an in-progress Yahoo daily bar can never enter the official Event Intelligence read.
A temporary provider failure may reuse a cache only when that cache already matches
the exact target session; prior-session readings are never relabeled current.
"""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "event_market_context.json"
SIGNAL_DATA = ROOT / "data" / "signal_data.json"
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


def _read_previous() -> dict:
    try:
        obj = json.loads(OUT.read_text())
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _target_session() -> pd.Timestamp:
    try:
        payload = json.loads(SIGNAL_DATA.read_text())
    except Exception as exc:
        raise RuntimeError(f"cannot read signal_data target session: {exc}") from exc
    raw = payload.get("market_date") or (payload.get("data_status") or {}).get("session_date")
    if not raw:
        raise RuntimeError("signal_data has no market_date/session_date target")
    target = pd.Timestamp(str(raw)[:10]).normalize()
    if pd.isna(target):
        raise RuntimeError(f"invalid target session: {raw}")
    return target


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
    idx = pd.to_datetime(close.index, errors="coerce")
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    close.index = idx
    close = close[~close.index.isna()].sort_index().dropna(how="all")
    missing = [t for t in TICKERS if t not in close.columns]
    if missing:
        raise RuntimeError(f"ETF history missing tickers: {missing}")
    return close


def _slice_to_target(close: pd.DataFrame, target: pd.Timestamp) -> pd.DataFrame:
    out = close.loc[close.index.normalize() <= target].copy()
    if out.empty:
        raise RuntimeError(f"ETF history has no rows through target session {target.date()}")
    for ticker in TICKERS:
        s = out[ticker].dropna()
        if s.empty:
            raise RuntimeError(f"{ticker}: no data through target session {target.date()}")
        latest = s.index[-1].normalize()
        if latest != target:
            raise RuntimeError(f"{ticker}: latest completed bar {latest.date()} does not match target {target.date()}")
    return out


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
    rsi = _rsi(s)
    return {
        "price": round(last, 3),
        "rsi14": None if rsi is None else round(rsi, 3),
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
    target = _target_session()
    close = _slice_to_target(_download(), target)
    market_date = target.date().isoformat()
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
        "version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "freshness": "current_provider",
        "confidence": "MODERATE",
        "source": "Yahoo Finance adjusted ETF history via yfinance",
        "target_session": market_date,
        "context": context,
        "error": None,
    }


def _fallback(previous: dict, error: str, target: pd.Timestamp) -> dict | None:
    ctx = previous.get("context") if isinstance(previous, dict) else None
    if not isinstance(ctx, dict) or str(ctx.get("market_date") or "") != target.date().isoformat():
        return None
    out = deepcopy(previous)
    out["generated_at"] = datetime.now(timezone.utc).isoformat()
    out["freshness"] = "same_session_fallback"
    out["confidence"] = "LOW"
    out["target_session"] = target.date().isoformat()
    out["error"] = error
    return out


def main() -> dict:
    previous = _read_previous()
    try:
        target = _target_session()
    except Exception as exc:
        target = None
        error = f"{type(exc).__name__}: {exc}"
        out = {
            "version": 2,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "freshness": "unavailable",
            "confidence": "LOW",
            "source": "Yahoo Finance adjusted ETF history via yfinance",
            "target_session": None,
            "context": {},
            "error": error,
        }
    else:
        try:
            out = build()
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            out = _fallback(previous, error, target) or {
                "version": 2,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "freshness": "unavailable",
                "confidence": "LOW",
                "source": "Yahoo Finance adjusted ETF history via yfinance",
                "target_session": target.date().isoformat(),
                "context": {},
                "error": error,
            }
    OUT.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    return out


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
