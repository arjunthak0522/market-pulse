#!/usr/bin/env python3
"""Intraday Market Pulse refresh.

Uses StockCharts $TRIN/$TRINQ as the canonical Arms-index definition and attempts
StockCharts quote extraction first. If StockCharts does not expose a parseable
quote in server HTML, uses the same raw Arms definition from a current quote
source rather than falling back to a prior-session value.

The historical event studies remain EOD/history based; only the current signal
snapshot is intraday-sensitive.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

import pandas as pd

import run_refresh as base

builder = base.builder


def _extract_quote(text: str, symbol: str) -> float | None:
    """Extract a quote from server-rendered/bootstrapped StockCharts markup."""
    patterns = [
        r'"lastPrice"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)',
        r'"last"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)',
        r'"close"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)',
        r'Last Price\s*</?[^>]*>*\s*([0-9]+(?:\.[0-9]+)?)',
        r'Last Price\s+([0-9]+(?:\.[0-9]+)?)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            value = float(m.group(1))
            if 0.02 <= value <= 25:
                return value
    return None


def stockcharts_quote(symbol: str) -> tuple[float, str, str]:
    encoded = "%24" + symbol.lstrip("$")
    urls = [
        f"https://stockcharts.com/sc3/ui/?s={encoded}",
        f"https://stockcharts.com/h-sc/ui?s={encoded}",
    ]
    errors = []
    for url in urls:
        try:
            r = builder.requests.get(url, headers=builder.UA, timeout=25)
            r.raise_for_status()
            value = _extract_quote(r.text, symbol)
            if value is not None:
                now = datetime.now(timezone.utc).isoformat()
                return value, now, f"StockCharts {symbol} intraday"
            errors.append(f"{url}: no parseable quote; html={len(r.text)} bytes")
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError(f"StockCharts {symbol} quote unavailable: {' | '.join(errors)}")


def barchart_quote(symbol: str) -> tuple[float, str, str]:
    # Current fallback using the same StockCharts/Arms definition. Never use a
    # prior-session cached value as an intraday substitute.
    page_symbol = "%24TRIN" if symbol == "$TRIN" else "%24TRIQ"
    url = f"https://www.barchart.com/stocks/quotes/{page_symbol}"
    text = builder.get(url).text
    clean = " ".join(builder.BeautifulSoup(text, "html.parser").stripped_strings)
    m = re.search(r"Last Price\s+([0-9]+(?:\.[0-9]+)?)", clean, re.I)
    if not m:
        raise RuntimeError(f"Barchart {symbol}: last price not found")
    return float(m.group(1)), datetime.now(timezone.utc).isoformat(), f"Barchart {symbol} current; StockCharts Arms definition"


def live_quote(symbol: str) -> tuple[float, str, str]:
    try:
        return stockcharts_quote(symbol)
    except Exception as exc:
        print(f"{symbol} StockCharts direct quote warning: {exc}")
        return barchart_quote(symbol)


def live_mcoscillator_current():
    # Keep the official NYMO/current NYSE breadth parser, but replace only TRIN
    # with an intraday canonical Arms quote.
    row = base._ORIGINAL_GET  # sentinel proving base module initialized
    del row
    data = builder.mcoscillator_current_original() if hasattr(builder, "mcoscillator_current_original") else None
    if data is None:
        # original builder function saved below before monkeypatch
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
        "TRIN and TRINQ use the StockCharts Arms-index definition and an intraday quote path; prior-session values are not accepted as current substitutes."
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

    # Replace the two current Arms readings only; their historical studies stay
    # based on the long-run underlying breadth/volume archive.
    builder.mcoscillator_current = live_mcoscillator_current
    builder.barchart_trinq = live_trinq_value

    builder.main()
    base.enrich_volatility_family()
    stamp_live_metadata()
    base.finalize_product_layer(previous_payload)


if __name__ == "__main__":
    main()
