#!/usr/bin/env python3
"""Intraday Market Pulse refresh.

StockCharts $TRIN/$TRINQ remain the canonical Arms-index definitions. Current
transport calculates the same classic Arms formula from intraday NYSE/Nasdaq
advancing/declining issues and advancing/declining volume. Prior-session values
are never substituted for an intraday snapshot.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

import run_refresh as base

builder = base.builder
ORIGINAL_MCOSCILLATOR = builder.mcoscillator_current


def tradingview_components(market: str) -> tuple[float, str, str, dict]:
    suffix = "NY" if market == "nyse" else "NQ"
    canonical = "$TRIN" if market == "nyse" else "$TRINQ"
    symbols = {
        "adv": f"USI:ADVN.{suffix}",
        "dec": f"USI:DECL.{suffix}",
        "upvol": f"USI:UPVOL.{suffix}",
        "dnvol": f"USI:DNVOL.{suffix}",
    }
    url = "https://scanner.tradingview.com/america/scan"
    body = {
        "symbols": {"tickers": list(symbols.values()), "query": {"types": []}},
        "columns": ["close", "update_mode"],
    }
    r = builder.requests.post(url, json=body, headers=builder.UA, timeout=20)
    r.raise_for_status()
    rows = r.json().get("data") or []
    by_symbol = {row.get("s"): row.get("d") for row in rows if row.get("s") and row.get("d")}
    vals = {}
    modes = []
    missing = []
    for key, sym in symbols.items():
        data = by_symbol.get(sym)
        if not data or data[0] is None:
            missing.append(sym)
            continue
        vals[key] = float(data[0])
        if len(data) > 1 and data[1] is not None:
            modes.append(str(data[1]))
    if missing:
        raise RuntimeError(f"TradingView {market} breadth missing: {', '.join(missing)}; returned={list(by_symbol)}")
    if min(vals.values()) <= 0:
        raise RuntimeError(f"TradingView {market} breadth invalid: {vals}")
    value = (vals["adv"] / vals["dec"]) / (vals["upvol"] / vals["dnvol"])
    if not (0.02 <= value <= 25):
        raise RuntimeError(f"TradingView {market} Arms invalid: {value} from {vals}")
    now = datetime.now(timezone.utc).isoformat()
    mode = ",".join(sorted(set(modes))) if modes else "intraday"
    source = f"TradingView USI {market.upper()} breadth components ({mode}); StockCharts {canonical} Arms definition"
    return value, now, source, vals


def live_quote(symbol: str) -> tuple[float, str, str]:
    market = "nyse" if symbol == "$TRIN" else "nasdaq"
    value, asof, source, components = tradingview_components(market)
    print(f"{symbol} live components: {components}; Arms={value:.4f}")
    return value, asof, source


def live_mcoscillator_current():
    data = ORIGINAL_MCOSCILLATOR()
    value, asof, source = live_quote("$TRIN")
    data["trin"] = value
    data["trin_as_of"] = asof
    data["trin_source"] = source
    return data


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
        "TRIN and TRINQ use the StockCharts classic Arms formula calculated from intraday exchange breadth components. Prior-session values are not accepted as current substitutes."
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
