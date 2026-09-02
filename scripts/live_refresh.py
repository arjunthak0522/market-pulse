#!/usr/bin/env python3
"""Current-session Market Pulse refresh.

Current market-state inputs come from same-session sources. StockCharts QuoteBrain
is used for its market-internal/index series; historical event studies remain
EOD/history based. Published EOD-only series are explicitly labeled EOD rather
than masquerading as live intraday readings.
"""
from __future__ import annotations

import io
import json
import math
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import pandas_market_calendars as mcal

import run_refresh as base

builder = base.builder
ORIGINAL_MCOSCILLATOR = builder.mcoscillator_current
ET = ZoneInfo("America/New_York")


def market_clock():
    now = datetime.now(timezone.utc)
    cal = mcal.get_calendar("NYSE")
    start = (now.astimezone(ET).date() - pd.Timedelta(days=5)).isoformat()
    end = (now.astimezone(ET).date() + pd.Timedelta(days=1)).isoformat()
    sched = cal.schedule(start_date=start, end_date=end)
    active = None
    last = None
    for idx, row in sched.iterrows():
        o = row["market_open"].to_pydatetime().astimezone(timezone.utc)
        c = row["market_close"].to_pydatetime().astimezone(timezone.utc)
        if o <= now <= c:
            active = (idx.date(), o, c)
        if c <= now:
            last = (idx.date(), o, c)
    if active:
        return {"open": True, "session_date": str(active[0]), "now": now}
    if last:
        return {"open": False, "session_date": str(last[0]), "now": now}
    return {"open": False, "session_date": str(now.astimezone(ET).date()), "now": now}


def _quote_time(row: dict):
    t = row.get("time")
    if isinstance(t, dict):
        ms = t.get("millis")
        if ms is not None:
            v = float(ms)
            if v > 10_000_000_000:
                v /= 1000
            return datetime.fromtimestamp(v, timezone.utc).isoformat(), t
        raw = t.get("time")
        zone = t.get("zone") or "America/New_York"
        if raw:
            dt = pd.Timestamp(raw).to_pydatetime().replace(tzinfo=ZoneInfo(zone))
            return dt.astimezone(timezone.utc).isoformat(), t
    for key in ("timestamp", "quoteTimestamp", "lastTimestamp", "dateTime", "datetime"):
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            if isinstance(value, (int, float)):
                v = float(value)
                if v > 10_000_000_000:
                    v /= 1000
                return datetime.fromtimestamp(v, timezone.utc).isoformat(), {key: value}
            dt = pd.to_datetime(value, utc=True, errors="coerce")
            if not pd.isna(dt):
                return dt.to_pydatetime().isoformat(), {key: value}
        except Exception:
            pass
    raise RuntimeError(f"StockCharts quote has no provider timestamp: {sorted(row)}")


def stockcharts_quotebrain(symbol: str):
    url = "https://stockcharts.com/quotebrain/quotes"
    params = {"s": symbol, "f": "json", "randomNumber": str(int(time.time() * 1000))}
    headers = dict(builder.UA)
    headers.update({"Referer": f"https://stockcharts.com/sc3/ui/?s=%24{symbol.lstrip('$')}", "Accept": "application/json,text/plain,*/*"})
    r = builder.requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    payload = r.json()
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise RuntimeError(f"StockCharts {symbol}: unexpected QuoteBrain payload")
    row = payload[0]
    value = builder.safe(row.get("close"))
    if value is None or not math.isfinite(value):
        raise RuntimeError(f"StockCharts {symbol}: missing/invalid close")
    asof, raw_time = _quote_time(row)
    print(f"{symbol}={value}; provider_time={raw_time}; realtime={row.get('realtime')}; source={row.get('source')}")
    return value, asof, f"StockCharts QuoteBrain {symbol}", row


def live_quote(symbol: str):
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


def current_mcclellan(market: str, adv: float, dec: float, session_date: str):
    links = builder.discover_unicorn_series()
    hist = builder.unicorn_market(market, links)[["adv", "dec"]].copy()
    d = pd.Timestamp(session_date)
    hist = hist[hist.index < d]
    hist.loc[d, ["adv", "dec"]] = [adv, dec]
    series = builder.mcclellan_from_ad(hist)
    return float(series.iloc[-1]), series


def _spark_closes(symbols):
    """Return {symbol: latest five valid daily closes} from Yahoo's multi-symbol spark endpoint."""
    out = {}
    url = "https://query1.finance.yahoo.com/v7/finance/spark"
    for i in range(0, len(symbols), 80):
        chunk = symbols[i:i + 80]
        params = {
            "symbols": ",".join(chunk),
            "range": "10d",
            "interval": "1d",
            "indicators": "close",
            "includeTimestamps": "true",
            "includePrePost": "false",
            "corsDomain": "finance.yahoo.com",
            ".tsrc": "finance",
        }
        try:
            r = builder.requests.get(url, params=params, headers=builder.UA, timeout=30)
            r.raise_for_status()
            result = (r.json().get("spark", {}) or {}).get("result") or []
            for item in result:
                symbol = item.get("symbol")
                response = item.get("response") or []
                if not symbol or not response:
                    continue
                closes = (((response[0].get("indicators") or {}).get("quote") or [{}])[0].get("close") or [])
                vals = [float(x) for x in closes if x is not None and math.isfinite(float(x))]
                if len(vals) >= 5:
                    out[symbol] = vals[-5:]
        except Exception as exc:
            print(f"Yahoo spark breadth chunk {i // 80 + 1} warning: {exc}")
        time.sleep(0.2)
    return out


def _chart_fallback(symbols, out):
    """Retry only missing constituents through the public chart endpoint."""
    for symbol in symbols:
        if symbol in out:
            continue
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            r = builder.requests.get(url, params={"range": "10d", "interval": "1d"}, headers=builder.UA, timeout=12)
            r.raise_for_status()
            result = (r.json().get("chart", {}).get("result") or [])
            if not result:
                continue
            closes = (((result[0].get("indicators") or {}).get("quote") or [{}])[0].get("close") or [])
            vals = [float(x) for x in closes if x is not None and math.isfinite(float(x))]
            if len(vals) >= 5:
                out[symbol] = vals[-5:]
        except Exception:
            continue
        if len(out) >= 490:
            break
    return out


def sp500_live_5d():
    """Current S&P 500 % above 5-day SMA from machine-readable current daily bars."""
    html = builder.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", timeout=30).text
    table = pd.read_html(io.StringIO(html))[0]
    tickers = table["Symbol"].astype(str).str.replace(".", "-", regex=False).tolist()
    closes = _spark_closes(tickers)
    if len(closes) < 450:
        closes = _chart_fallback(tickers, closes)
    nvalid = len(closes)
    print(f"S&P 500 5D breadth machine-readable valid={nvalid}")
    if nvalid < 450:
        raise RuntimeError(f"S&P 500 live 5-day breadth has only {nvalid} valid constituents")
    above = sum(1 for vals in closes.values() if vals[-1] > sum(vals) / 5)
    return round(100 * above / nvalid, 2)


def overlay_current_session():
    payload = json.loads(builder.OUT.read_text())
    clock = market_clock()
    session = clock["session_date"]
    sig = payload["signals"]

    q = {}
    for symbol in (
        "$CPCE","$NYADV","$NYDEC","$NYHGH","$NYLOW","$NYTOT","$NYMO","$TRIN",
        "$NAADV","$NADEC","$NAHGH","$NALOW","$NATOT","$NAMO","$TRINQ",
        "$SPXA20R","$SPXA50R","$SPXA200R","$VIX","$VIX3M","$VVIX","$SKEW"
    ):
        q[symbol] = stockcharts_quotebrain(symbol)

    def stamp(row, symbol, *, frequency="intraday"):
        _v, ts, src, raw = q[symbol]
        provider_date = str(datetime.fromisoformat(ts).astimezone(ET).date())
        row.update({
            "as_of": provider_date,
            "as_of_timestamp": ts,
            "source": src,
            "freshness": "intraday" if frequency == "intraday" and clock["open"] else ("session_close" if frequency == "intraday" else "eod"),
            "frequency": frequency,
            "quote_transport": "StockCharts QuoteBrain",
            "provider_realtime_flag": bool(raw.get("realtime")),
        })

    cpce = q["$CPCE"][0]
    sig["cpce"]["value"] = round(cpce, 3)
    stamp(sig["cpce"], "$CPCE", frequency="eod")

    trin_raw = q["$TRIN"][3]
    trinq_raw = q["$TRINQ"][3]
    sig["trin"].update({
        "value": round(q["$TRIN"][0], 3),
        "session_open": builder.safe(trin_raw.get("open")),
        "session_high": builder.safe(trin_raw.get("high")),
        "session_low": builder.safe(trin_raw.get("low")),
        "definition": "StockCharts $TRIN / classic NYSE Arms Index",
    })
    sig["trin"]["intraday_extreme_occurred"] = bool(
        sig["trin"].get("session_high") is not None and
        sig["trin"].get("study", {}).get("threshold") is not None and
        sig["trin"]["session_high"] >= sig["trin"]["study"]["threshold"]
    )
    stamp(sig["trin"], "$TRIN")

    sig["trinq"].update({
        "value": round(q["$TRINQ"][0], 3),
        "session_open": builder.safe(trinq_raw.get("open")),
        "session_high": builder.safe(trinq_raw.get("high")),
        "session_low": builder.safe(trinq_raw.get("low")),
        "definition": "StockCharts $TRINQ / classic Nasdaq Arms Index",
    })
    sig["trinq"]["intraday_extreme_occurred"] = bool(
        sig["trinq"].get("session_high") is not None and
        sig["trinq"].get("study", {}).get("threshold") is not None and
        sig["trinq"]["session_high"] >= sig["trinq"]["study"]["threshold"]
    )
    stamp(sig["trinq"], "$TRINQ")

    if clock["open"]:
        nymo, nymo_hist = current_mcclellan("nyse", q["$NYADV"][0], q["$NYDEC"][0], session)
        namo, namo_hist = current_mcclellan("nasdaq", q["$NAADV"][0], q["$NADEC"][0], session)
        sig["nymo"].update({"value": round(nymo, 2), "percentile_252d": builder.pct_rank(nymo_hist.iloc[:-1], nymo), "as_of": session, "as_of_timestamp": q["$NYADV"][1], "source": "StockCharts intraday NYSE advances/declines; ratio-adjusted McClellan calculation", "freshness": "intraday", "frequency": "intraday_calculated"})
        sig["namo"].update({"value": round(namo, 2), "percentile_252d": builder.pct_rank(namo_hist.iloc[:-1], namo), "as_of": session, "as_of_timestamp": q["$NAADV"][1], "source": "StockCharts intraday Nasdaq advances/declines; ratio-adjusted McClellan calculation", "freshness": "intraday", "frequency": "intraday_calculated"})
    else:
        sig["nymo"]["value"] = round(q["$NYMO"][0], 2)
        stamp(sig["nymo"], "$NYMO", frequency="eod")
        sig["namo"]["value"] = round(q["$NAMO"][0], 2)
        stamp(sig["namo"], "$NAMO", frequency="eod")

    ny_lows, ny_highs, ny_tot = q["$NYLOW"][0], q["$NYHGH"][0], q["$NYTOT"][0]
    na_lows, na_highs, na_tot = q["$NALOW"][0], q["$NAHGH"][0], q["$NATOT"][0]
    ny_low_pct = 100 * ny_lows / ny_tot if ny_tot else None
    ny_ts = q["$NYLOW"][1]
    sig["newlows"].update({
        "value": round(ny_lows), "new_highs": round(ny_highs), "new_low_pct": round(ny_low_pct, 2),
        "nasdaq_new_lows": round(na_lows), "nasdaq_new_highs": round(na_highs), "nasdaq_new_low_pct": round(100 * na_lows / na_tot, 2) if na_tot else None,
        "as_of": str(datetime.fromisoformat(ny_ts).astimezone(ET).date()), "as_of_timestamp": ny_ts,
        "source": "StockCharts NYSE/Nasdaq intraday 52-week highs/lows", "freshness": "intraday" if clock["open"] else "session_close", "frequency": "intraday"
    })

    live5 = sp500_live_5d()
    breadth_ts = q["$SPXA20R"][1]
    sig["breadth"].update({
        "above_5d": live5,
        "above_20d": round(q["$SPXA20R"][0], 2),
        "above_50d": round(q["$SPXA50R"][0], 2),
        "above_200d": round(q["$SPXA200R"][0], 2),
        "as_of": str(datetime.fromisoformat(breadth_ts).astimezone(ET).date()), "as_of_timestamp": breadth_ts,
        "source": "Current S&P 500 constituent 5-day breadth + StockCharts 20/50/200-day participation",
        "freshness": "intraday" if clock["open"] else "session_close", "frequency": "intraday"
    })
    hist = json.loads(builder.HISTORY.read_text())
    br = pd.DataFrame(hist.get("breadth", []))
    if not br.empty and "above_5d" in br:
        sig["breadth"]["percentile_252d"] = builder.pct_rank(pd.to_numeric(br["above_5d"], errors="coerce"), live5)

    vix, vix3m, vvix, skew = q["$VIX"][0], q["$VIX3M"][0], q["$VVIX"][0], q["$SKEW"][0]
    term = vix / vix3m
    vh = builder.cboe_series("VIX")
    v3h = builder.cboe_series("VIX3M")
    vvh = builder.cboe_series("VVIX")
    skh = builder.cboe_series("SKEW")
    termh = pd.concat([vh.rename("v"), v3h.rename("v3")], axis=1).dropna().eval("v/v3")
    vol_ts = q["$VIX"][1]
    skew_ts = q["$SKEW"][1]
    sig["vol"].update({
        "vix": round(vix, 2), "vix3m": round(vix3m, 2), "term_ratio": round(term, 3), "vvix": round(vvix, 2), "skew": round(skew, 2),
        "term_percentile_252d": builder.pct_rank(termh, term), "vvix_percentile_252d": builder.pct_rank(vvh, vvix), "skew_percentile_252d": builder.pct_rank(skh, skew),
        "as_of": str(datetime.fromisoformat(vol_ts).astimezone(ET).date()), "as_of_timestamp": vol_ts,
        "source": "StockCharts current VIX/VIX3M/VVIX; StockCharts SKEW EOD",
        "freshness": "intraday" if clock["open"] else "session_close", "frequency": "mixed_intraday_eod",
        "skew_freshness": "eod", "skew_as_of": str(datetime.fromisoformat(skew_ts).astimezone(ET).date()), "skew_as_of_timestamp": skew_ts
    })

    payload["market_date"] = session
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    payload.setdefault("methodology", {})["live_data"] = (
        "Market Pulse uses same-session current inputs. TRIN/TRINQ, exchange breadth, new highs/lows and VIX-family inputs refresh intraday; NYMO/NAMO are calculated intraday from live A/D counts; CPCE and SKEW are explicitly EOD publications and are never mislabeled as intraday."
    )
    payload["data_status"] = {"session_date": session, "market_open": clock["open"], "generated_at": payload["generated_at"]}
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
    overlay_current_session()
    base.finalize_product_layer(previous_payload)


if __name__ == "__main__":
    main()
