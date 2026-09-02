#!/usr/bin/env python3
"""Intraday Market Pulse refresh.

StockCharts $TRIN/$TRINQ remain the canonical Arms-index definitions. Current
transport uses machine-readable intraday market-breadth symbols and never
substitutes an older completed-session value during an intraday refresh.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from urllib.parse import quote

import pandas as pd

import run_refresh as base

builder = base.builder


def stockcharts_quote(symbol: str) -> tuple[float, str, str]:
    encoded = "%24" + symbol.lstrip("$")
    url = f"https://stockcharts.com/sc3/ui/?s={encoded}"
    r = builder.requests.get(url, headers=builder.UA, timeout=25)
    r.raise_for_status()
    patterns = [
        r'"lastPrice"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)',
        r'"last"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)',
    ]
    for pat in patterns:
        m = re.search(pat, r.text, re.I)
        if m:
            value = float(m.group(1))
            if 0.02 <= value <= 25:
                return value, datetime.now(timezone.utc).isoformat(), f"StockCharts {symbol} intraday"
    raise RuntimeError(f"StockCharts {symbol} interactive shell does not expose quote server-side")


def tradingview_quote(symbol: str) -> tuple[float, str, str]:
    tv_symbol = "USI:TRIN.NY" if symbol == "$TRIN" else "USI:TRIN.NQ"
    url = "https://scanner.tradingview.com/america/scan"
    body = {
        "symbols": {"tickers": [tv_symbol], "query": {"types": []}},
        "columns": ["close", "update_mode"],
    }
    r = builder.requests.post(url, json=body, headers=builder.UA, timeout=20)
    r.raise_for_status()
    payload = r.json()
    rows = payload.get("data") or []
    if not rows or not rows[0].get("d"):
        raise RuntimeError(f"TradingView {tv_symbol}: no data")
    value = float(rows[0]["d"][0])
    if not (0.02 <= value <= 25):
        raise RuntimeError(f"TradingView {tv_symbol}: invalid value {value}")
    mode = rows[0]["d"][1] if len(rows[0]["d"]) > 1 else None
    return value, datetime.now(timezone.utc).isoformat(), f"TradingView {tv_symbol} intraday transport ({mode}); StockCharts {symbol} definition"


def yahoo_chart_quote(symbols: list[str], canonical: str) -> tuple[float, str, str]:
    errors = []
    now = datetime.now(timezone.utc)
    for sym in symbols:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(sym, safe='')}?interval=1m&range=1d"
            r = builder.requests.get(url, headers=builder.UA, timeout=20)
            r.raise_for_status()
            result = (r.json().get("chart", {}).get("result") or [])[0]
            meta = result.get("meta", {})
            value = meta.get("regularMarketPrice")
            ts = meta.get("regularMarketTime")
            if value is None or ts is None:
                errors.append(f"{sym}: missing current price/time")
                continue
            asof_dt = datetime.fromtimestamp(int(ts), timezone.utc)
            age_min = (now - asof_dt).total_seconds() / 60
            if age_min > 24 * 60:
                errors.append(f"{sym}: stale by {age_min:.0f}m")
                continue
            value = float(value)
            if not (0.02 <= value <= 25):
                errors.append(f"{sym}: invalid value {value}")
                continue
            return value, asof_dt.isoformat(), f"Yahoo {sym} intraday transport; StockCharts {canonical} definition"
        except Exception as exc:
            errors.append(f"{sym}: {exc}")
    raise RuntimeError("Yahoo Arms quote unavailable: " + " | ".join(errors))


def live_quote(symbol: str) -> tuple[float, str, str]:
    try:
        return stockcharts_quote(symbol)
    except Exception as exc:
        print(f"{symbol} StockCharts transport warning: {exc}")
    try:
        return tradingview_quote(symbol)
    except Exception as exc:
        print(f"{symbol} TradingView transport warning: {exc}")
    candidates = ["C:TRIN", "^TRIN"] if symbol == "$TRIN" else ["C:TRINQ", "^TRINQ", "C:TRIN.NQ"]
    return yahoo_chart_quote(candidates, symbol)


def live_mcoscillator_current():
    data = ORIGINAL_MCOSCILLATOR()
    value, asof, source = live_quote("$TRIN")
    data["trin"] = value
    data["trin_as_of"] = asof
    data["trin_source"] = source
    return data


ORIGINAL_MCOSCILLATOR = builder.mcoscillator_current


def live_trinq_value():
    value, _asof, _source = live_quote("$TRINQ")
    return value


def stamp_live_metadata():
    payload = json.loads(builder.OUT.read_text())
    now = datetime.now(timezone.utc).isoformat()
    trin_v, trin_ts, trin_src = live_quote("$TRIN")
    trinq_v, trinq_ts, trinq_src = live_quote("$TRINQ")
    payload["signals"]["trin"].update({
        "value": round(trin_v, 3),
        "as_of_timestamp": trin_ts,
        "source": trin_src,
        "freshness": "intraday",
        "definition": "StockCharts $TRIN / classic NYSE Arms Index",
    })
    payload["signals"]["trinq"].update({
        "value": round(trinq_v, 3),
        "as_of_timestamp": trinq_ts,
        "source": trinq_src,
        "freshness": "intraday",
        "definition": "StockCharts $TRINQ / classic Nasdaq Arms Index",
    })
    payload["generated_at"] = now
    payload.setdefault("methodology", {})["live_data"] = (
        "TRIN and TRINQ use the StockCharts Arms-index definition with machine-readable intraday transport. Prior-session values are not accepted as current substitutes."
    )
    builder.OUT.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def main():
    previous_payload = None
    if builder.OUT.exists():
        try:
            previous_payload = json.loads(builder.OUT.read_text())
        except Exception:
            previous_payload = None

    builder.spy_history = base.github_spy_history
    builder.get = base.source_get
    builder.read_unicorn_series = base.archive_series
    builder.nasdaq_daily = base.official_nasdaq_daily
    builder.local_frames = base.long_history_frames
    builder.event_study = base.episode_event_study
    pd.Series.skew = property(base.series_skew_column)

    builder.mcoscillator_current = live_mcoscillator_current
    builder.barchart_trinq = live_trinq_value

    builder.main()
    base.enrich_volatility_family()
    stamp_live_metadata()
    base.finalize_product_layer(previous_payload)


if __name__ == "__main__":
    main()
