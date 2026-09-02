#!/usr/bin/env python3
"""Intraday Market Pulse refresh.

StockCharts $TRIN/$TRINQ remain the canonical Arms-index definitions. Current
transport prefers a machine-readable intraday quote endpoint and never substitutes
an older completed-session value during an intraday refresh.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from urllib.parse import quote

import pandas as pd

import run_refresh as base

builder = base.builder


def _extract_quote(text: str) -> float | None:
    patterns = [
        r'"lastPrice"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)',
        r'"regularMarketPrice"\s*:\s*(?:\{"raw":)?\s*([0-9]+(?:\.[0-9]+)?)',
        r'"last"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)',
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
    url = f"https://stockcharts.com/sc3/ui/?s={encoded}"
    r = builder.requests.get(url, headers=builder.UA, timeout=25)
    r.raise_for_status()
    value = _extract_quote(r.text)
    if value is None:
        raise RuntimeError(f"StockCharts {symbol} interactive shell does not expose quote server-side")
    return value, datetime.now(timezone.utc).isoformat(), f"StockCharts {symbol} intraday"


def yahoo_chart_quote(symbols: list[str], canonical: str) -> tuple[float, str, str]:
    errors = []
    for sym in symbols:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(sym, safe='')}?interval=1m&range=1d"
            r = builder.requests.get(url, headers=builder.UA, timeout=20)
            r.raise_for_status()
            payload = r.json()
            result = payload.get("chart", {}).get("result") or []
            if not result:
                errors.append(f"{sym}: no result")
                continue
            meta = result[0].get("meta", {})
            value = meta.get("regularMarketPrice")
            ts = meta.get("regularMarketTime")
            if value is None:
                closes = (result[0].get("indicators", {}).get("quote") or [{}])[0].get("close") or []
                value = next((x for x in reversed(closes) if x is not None), None)
            value = float(value) if value is not None else None
            if value is None or not (0.02 <= value <= 25):
                errors.append(f"{sym}: invalid value {value}")
                continue
            asof = datetime.fromtimestamp(int(ts), timezone.utc).isoformat() if ts else datetime.now(timezone.utc).isoformat()
            return value, asof, f"Yahoo {sym} intraday transport; StockCharts {canonical} definition"
        except Exception as exc:
            errors.append(f"{sym}: {exc}")
    raise RuntimeError("Yahoo Arms quote unavailable: " + " | ".join(errors))


def barchart_quote(symbol: str) -> tuple[float, str, str]:
    page_symbol = "%24TRIN" if symbol == "$TRIN" else "%24TRIQ"
    url = f"https://www.barchart.com/stocks/quotes/{page_symbol}"
    text = builder.get(url).text
    clean = " ".join(builder.BeautifulSoup(text, "html.parser").stripped_strings)
    m = re.search(r"Last Price\s+([0-9]+(?:\.[0-9]+)?)", clean, re.I)
    if not m:
        raise RuntimeError(f"Barchart {symbol}: last price not found")
    return float(m.group(1)), datetime.now(timezone.utc).isoformat(), f"Barchart {symbol} intraday transport; StockCharts Arms definition"


def live_quote(symbol: str) -> tuple[float, str, str]:
    try:
        return stockcharts_quote(symbol)
    except Exception as exc:
        print(f"{symbol} StockCharts transport warning: {exc}")
    candidates = ["C:TRIN", "^TRIN"] if symbol == "$TRIN" else ["C:TRINQ", "^TRINQ", "C:TRIN.NQ"]
    try:
        return yahoo_chart_quote(candidates, symbol)
    except Exception as exc:
        print(f"{symbol} Yahoo transport warning: {exc}")
    return barchart_quote(symbol)


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
