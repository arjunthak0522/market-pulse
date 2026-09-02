#!/usr/bin/env python3
"""Intraday Market Pulse refresh.

TRIN and TRINQ are fetched from the same StockCharts QuoteBrain service used by
its current chart application. Historical event studies remain history/EOD based.
No prior-session quote is accepted as an intraday substitute.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import pandas as pd

import run_refresh as base

builder = base.builder
ORIGINAL_MCOSCILLATOR = builder.mcoscillator_current


def _quote_time(row: dict) -> tuple[str, dict]:
    """Return best available quote timestamp plus the raw time metadata."""
    keys = ("timestamp", "quoteTimestamp", "lastTimestamp", "lastTime", "dateTime", "datetime", "date", "time")
    raw = {k: row.get(k) for k in keys if row.get(k) not in (None, "")}
    for k, value in raw.items():
        try:
            if isinstance(value, (int, float)):
                # tolerate seconds or milliseconds
                v = float(value)
                if v > 10_000_000_000:
                    v /= 1000
                return datetime.fromtimestamp(v, timezone.utc).isoformat(), raw
            dt = pd.to_datetime(value, utc=True, errors="coerce")
            if not pd.isna(dt):
                return dt.to_pydatetime().isoformat(), raw
        except Exception:
            pass
    # QuoteBrain does not necessarily expose a timestamp field in all symbol
    # payloads. In that case retain retrieval time but separately record that it
    # is retrieval time, not an exchange timestamp.
    return datetime.now(timezone.utc).isoformat(), raw


def stockcharts_quotebrain(symbol: str) -> tuple[float, str, str, dict]:
    url = "https://stockcharts.com/quotebrain/quotes"
    params = {"s": symbol, "f": "json", "randomNumber": str(int(time.time() * 1000))}
    headers = dict(builder.UA)
    headers.update({"Referer": f"https://stockcharts.com/sc3/ui/?s=%24{symbol.lstrip('$')}", "Accept": "application/json,text/plain,*/*"})
    r = builder.requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    payload = r.json()
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise RuntimeError(f"StockCharts {symbol}: unexpected QuoteBrain payload {type(payload).__name__}: {str(payload)[:300]}")
    row = payload[0]
    value = row.get("close")
    if value is None:
        raise RuntimeError(f"StockCharts {symbol}: QuoteBrain missing close; keys={sorted(row)}")
    value = float(value)
    if not (0.02 <= value <= 25):
        raise RuntimeError(f"StockCharts {symbol}: invalid close {value}")
    asof, raw_time = _quote_time(row)
    print(f"{symbol} StockCharts QuoteBrain close={value}; time_meta={raw_time}; keys={sorted(row)}")
    return value, asof, f"StockCharts QuoteBrain {symbol}", row


def live_quote(symbol: str) -> tuple[float, str, str]:
    value, asof, source, _ = stockcharts_quotebrain(symbol)
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
    trin_v, trin_ts, trin_src, trin_raw = stockcharts_quotebrain("$TRIN")
    trinq_v, trinq_ts, trinq_src, trinq_raw = stockcharts_quotebrain("$TRINQ")
    payload["signals"]["trin"].update({
        "value": round(trin_v, 3),
        "as_of_timestamp": trin_ts,
        "source": trin_src,
        "freshness": "intraday",
        "definition": "StockCharts $TRIN / classic NYSE Arms Index",
        "quote_transport": "StockCharts QuoteBrain",
    })
    payload["signals"]["trinq"].update({
        "value": round(trinq_v, 3),
        "as_of_timestamp": trinq_ts,
        "source": trinq_src,
        "freshness": "intraday",
        "definition": "StockCharts $TRINQ / classic Nasdaq Arms Index",
        "quote_transport": "StockCharts QuoteBrain",
    })
    payload["generated_at"] = now
    payload.setdefault("methodology", {})["live_data"] = (
        "TRIN and TRINQ are fetched from StockCharts QuoteBrain, the quote service used by its chart app. Prior-session values are not accepted as current substitutes."
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
