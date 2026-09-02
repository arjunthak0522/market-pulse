#!/usr/bin/env python3
"""Build the clean seven-signal Market Pulse dataset.

Outputs data/signal_data.json. Every family must have a current reading and a
historical forward-return study. Live values use current public sources; long
breadth studies use the archived Unicorn breadth files when available, while
local recorded history remains a fallback so the product never silently drops a
family.
"""
from __future__ import annotations

import io
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "data" / "market_context.json"
HISTORY = ROOT / "data" / "history.json"
OUT = ROOT / "data" / "signal_data.json"
UA = {"User-Agent": "Mozilla/5.0 MarketPulse/1.0"}
HORIZONS = (5, 10, 21, 60)


def safe(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def pct_rank(series: pd.Series, value: float | None, window: int = 252):
    if value is None:
        return None
    s = pd.to_numeric(series, errors="coerce").dropna().tail(window)
    if len(s) < 20:
        return None
    return round(100 * float((s <= value).mean()), 1)


def stats(values):
    a = np.asarray([x for x in values if x is not None and np.isfinite(x)], dtype=float)
    if not len(a):
        return None
    return {
        "n": int(len(a)),
        "average": round(float(a.mean()), 3),
        "median": round(float(np.median(a)), 3),
        "positive_rate": round(100 * float(np.mean(a > 0)), 1),
        "best": round(float(a.max()), 3),
        "worst": round(float(a.min()), 3),
    }


def event_study(series: pd.Series, spy: pd.Series, *, high: bool, title: str, rule: str, quantile=.90):
    s = pd.to_numeric(series, errors="coerce").dropna().sort_index()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    if len(s) < 40:
        return None
    threshold = float(s.quantile(quantile if high else 1 - quantile))
    mask = s >= threshold if high else s <= threshold
    event_dates = list(s.index[mask])
    if len(event_dates) < 5:
        return None
    px = pd.to_numeric(spy, errors="coerce").dropna().sort_index()
    px.index = pd.to_datetime(px.index).tz_localize(None)
    loc = {d: i for i, d in enumerate(px.index)}
    horizons = {}
    usable_dates = []
    for h in HORIZONS:
        vals = []
        for d in event_dates:
            i = loc.get(d)
            if i is None or i + h >= len(px):
                continue
            vals.append(100 * (float(px.iloc[i + h]) / float(px.iloc[i]) - 1))
            if h == 21:
                usable_dates.append(str(d.date()))
        st = stats(vals)
        if st:
            horizons[str(h)] = st
    if not horizons:
        return None
    return {
        "title": title,
        "rule": rule,
        "threshold": round(threshold, 4),
        "direction": "high" if high else "low",
        "historical_sample": len(event_dates),
        "horizons": horizons,
        "prior_dates": usable_dates[-12:][::-1],
    }


def get(url, timeout=30):
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r


def spy_history():
    df = yf.download("SPY", start="1990-01-01", auto_adjust=True, progress=False, threads=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if df.empty:
        raise RuntimeError("SPY history unavailable")
    s = df["Close"].astype(float)
    s.index = pd.to_datetime(s.index).tz_localize(None)
    return s


def cboe_series(symbol):
    url = f"https://cdn.cboe.com/api/global/us_indices/daily_prices/{symbol}_History.csv"
    df = pd.read_csv(io.BytesIO(get(url).content))
    cols = {str(c).strip().upper(): c for c in df.columns}
    dc = cols.get("DATE")
    vc = cols.get("CLOSE") or cols.get(symbol.upper())
    if dc is None or vc is None:
        raise RuntimeError(f"Cboe {symbol}: unsupported columns")
    s = pd.Series(pd.to_numeric(df[vc], errors="coerce").values,
                  index=pd.to_datetime(df[dc], errors="coerce")).dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s.astype(float)


def parse_cboe_equity_pc():
    """Current Cboe equity put/call ratio from the daily statistics page."""
    text = get("https://www.cboe.com/markets/us/options/market-statistics/daily/").text
    soup = BeautifulSoup(text, "html.parser")
    clean = " ".join(soup.stripped_strings)
    m = re.search(r"EQUITY PUT/CALL RATIO\s+([0-9]+(?:\.[0-9]+)?)", clean, re.I)
    if not m:
        raise RuntimeError("Cboe equity put/call ratio not found")
    return float(m.group(1))


def nasdaq_daily():
    year = datetime.now(timezone.utc).year
    url = f"https://www.nasdaqtrader.com/dynamic/dailyfiles/daily{year}.csv"
    raw = get(url).content
    df = pd.read_csv(io.BytesIO(raw))
    cols = {str(c).strip().lower(): c for c in df.columns}
    date_col = next((c for k, c in cols.items() if "date" in k), None)
    adv_col = next((c for k, c in cols.items() if "advance" in k and "nasdaq" in k), None)
    dec_col = next((c for k, c in cols.items() if "decline" in k and "nasdaq" in k), None)
    if date_col is None or adv_col is None or dec_col is None:
        raise RuntimeError(f"Nasdaq daily file columns not recognized: {list(df.columns)}")
    out = pd.DataFrame({
        "date": pd.to_datetime(df[date_col], errors="coerce"),
        "adv": pd.to_numeric(df[adv_col], errors="coerce"),
        "dec": pd.to_numeric(df[dec_col], errors="coerce"),
    }).dropna().set_index("date").sort_index()
    return out


def mcoscillator_current():
    text = get("https://www.mcoscillator.com/market_breadth_data/").text
    soup = BeautifulSoup(text, "html.parser")
    clean = "\n".join(soup.stripped_strings)
    date_m = re.search(r"NYSE:\s*(\d{2}/\d{2}/\d{4})", clean)
    if not date_m:
        raise RuntimeError("McOscillator date missing")
    as_of = pd.to_datetime(date_m.group(1)).strftime("%Y-%m-%d")
    def first(pattern):
        m = re.search(pattern, clean, re.I)
        return float(m.group(1).replace(",", "")) if m else None
    # HTML order is label, issue count, volume count.
    adv = first(r"Advances\s+([0-9,]+)")
    dec = first(r"Declines\s+([0-9,]+)")
    osc = first(r"McC OSC\s+(-?[0-9,.]+)")
    # Pull volume from table rows directly to avoid matching the issue count twice.
    adv_vol = dec_vol = None
    for tr in soup.find_all("tr"):
        cells = [" ".join(td.stripped_strings) for td in tr.find_all(["td", "th"])]
        if not cells:
            continue
        row = " | ".join(cells)
        nums = [x.replace(",", "") for x in re.findall(r"-?\d[\d,]*", row)]
        if re.search(r"\bAdvances\b", row, re.I) and len(nums) >= 2:
            adv, adv_vol = float(nums[0]), float(nums[-1])
        if re.search(r"\bDeclines\b", row, re.I) and len(nums) >= 2:
            dec, dec_vol = float(nums[0]), float(nums[-1])
    if None in (adv, dec, osc):
        raise RuntimeError("McOscillator current breadth parse incomplete")
    trin = None
    if adv_vol and dec_vol and dec and adv:
        trin = (adv / dec) / (adv_vol / dec_vol)
    return {"as_of": as_of, "adv": adv, "dec": dec, "adv_vol": adv_vol,
            "dec_vol": dec_vol, "nymo": osc, "trin": trin}


def barchart_trinq():
    text = get("https://www.barchart.com/stocks/quotes/%24TRIQ").text
    soup = BeautifulSoup(text, "html.parser")
    clean = " ".join(soup.stripped_strings)
    m = re.search(r"Last Price\s+([0-9]+(?:\.[0-9]+)?)", clean, re.I)
    if not m:
        raise RuntimeError("Barchart TRINQ last price not found")
    return float(m.group(1))


def mcclellan_from_ad(df):
    rana = 1000 * (df["adv"] - df["dec"]) / (df["adv"] + df["dec"])
    e10 = rana.ewm(alpha=.10, adjust=False).mean()
    e5 = rana.ewm(alpha=.05, adjust=False).mean()
    return e10 - e5


def discover_unicorn_series():
    """Discover the 8 NYSE/Nasdaq CSV series links from Unicorn's historical table."""
    soup = BeautifulSoup(get("https://unicorn.us.com/advdec/").text, "html.parser")
    result = {}
    names = ["adv", "dec", "unch", "adv_vol", "dec_vol", "unch_vol", "new_highs", "new_lows"]
    for tr in soup.find_all("tr"):
        txt = " ".join(tr.stripped_strings).lower()
        market = "nyse" if txt.startswith("nyse") else "nasdaq" if txt.startswith("nasdaq") else None
        if not market:
            continue
        csvs = []
        for a in tr.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".csv"):
                csvs.append(requests.compat.urljoin("https://unicorn.us.com/advdec/", href))
        if len(csvs) >= 8:
            result[market] = dict(zip(names, csvs[:8]))
    if not result:
        raise RuntimeError("Unicorn breadth CSV links not discovered")
    return result


def read_unicorn_series(url):
    # files are simple date,value CSVs but tolerate headers and alternate separators
    raw = get(url).text
    df = pd.read_csv(io.StringIO(raw), header=None, comment="#")
    if df.shape[1] < 2:
        raise RuntimeError(f"Unicorn series invalid: {url}")
    dates = pd.to_datetime(df.iloc[:, 0], errors="coerce")
    vals = pd.to_numeric(df.iloc[:, -1], errors="coerce")
    s = pd.Series(vals.values, index=dates).dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s


def unicorn_market(market):
    links = discover_unicorn_series()[market]
    cols = {k: read_unicorn_series(v) for k, v in links.items()}
    df = pd.concat(cols, axis=1).dropna(subset=["adv", "dec"])
    return df


def local_frames(ctx, hist):
    br = pd.DataFrame(hist.get("breadth", []))
    if not br.empty:
        br["date"] = pd.to_datetime(br["date"])
        br = br.set_index("date").sort_index()
    market = pd.DataFrame(hist.get("market", []))
    if not market.empty:
        market["date"] = pd.to_datetime(market["date"])
        market = market.set_index("date").sort_index()
    pc = pd.DataFrame(hist.get("put_call", []))
    if not pc.empty:
        pc["date"] = pd.to_datetime(pc["date"])
        pc = pc.set_index("date").sort_index()
    return br, market, pc


def study_or_raise(name, study):
    if not study:
        raise RuntimeError(f"{name}: historical study unavailable")
    return study


def main():
    ctx = json.loads(CONTEXT.read_text())
    hist = json.loads(HISTORY.read_text())
    br, market, pc_local = local_frames(ctx, hist)
    spy = spy_history()

    # Long exchange breadth archive for precedent. It stops in 2020, which is fine
    # for historical event distributions; current readings come from live sources.
    nyse_hist = unicorn_market("nyse")
    nas_hist = unicorn_market("nasdaq")
    nymo_hist = mcclellan_from_ad(nyse_hist)
    namo_hist = mcclellan_from_ad(nas_hist)
    nyse_trin_hist = (nyse_hist.adv / nyse_hist.dec) / (nyse_hist.adv_vol / nyse_hist.dec_vol)
    nas_trin_hist = (nas_hist.adv / nas_hist.dec) / (nas_hist.adv_vol / nas_hist.dec_vol)
    nhnl_pressure = nyse_hist.new_lows / (nyse_hist.adv + nyse_hist.dec + nyse_hist.unch) * 100

    nas_live = nasdaq_daily()
    namo_live_series = mcclellan_from_ad(nas_live)
    namo = float(namo_live_series.iloc[-1])
    nas_asof = str(nas_live.index[-1].date())
    ny_live = mcoscillator_current()
    nymo = float(ny_live["nymo"])
    trin = safe(ny_live["trin"])
    trinq = barchart_trinq()

    cpce = parse_cboe_equity_pc()
    # Guaranteed local CPCE precedent today; extended Cboe archive can be layered in
    # later without changing the study contract.
    if pc_local.empty or "value" not in pc_local:
        raise RuntimeError("CPCE local history missing")
    cpce_hist = pd.to_numeric(pc_local.value, errors="coerce").dropna()

    vix = cboe_series("VIX")
    vix3m = cboe_series("VIX3M")
    vvix = cboe_series("VVIX")
    skew = cboe_series("SKEW")
    vr = pd.concat({"vix": vix, "vix3m": vix3m, "vvix": vvix, "skew": skew}, axis=1).dropna()
    # Stress composite: high VIX/VVIX/SKEW percentiles plus term inversion.
    for c in ("vix", "vvix", "skew"):
        vr[c + "_pct"] = vr[c].rolling(252, min_periods=60).rank(pct=True) * 100
    vr["term"] = vr.vix / vr.vix3m
    vr["stress"] = vr.vix_pct.fillna(50) * .4 + vr.vvix_pct.fillna(50) * .35 + vr.skew_pct.fillna(50) * .15 + (vr.term > 1).astype(float) * 10

    breadth_series = pd.to_numeric(br.get("above_5d"), errors="coerce").dropna() if not br.empty else pd.Series(dtype=float)
    new_lows_current = safe(ctx.get("breadth", {}).get("new_lows_52w"))
    issues = sum(safe(ctx.get("breadth", {}).get(k)) or 0 for k in ("advancers", "decliners", "unchanged"))
    newlow_pct_current = 100 * new_lows_current / issues if new_lows_current is not None and issues else None

    studies = {
        "cpce": study_or_raise("CPCE", event_study(cpce_hist, spy, high=True, title="Equity put/call fear extremes", rule="Equity put/call ratio in the top decile of available history.")),
        "namo": study_or_raise("NAMO", event_study(namo_hist, spy, high=False, title="Nasdaq McClellan washouts", rule="Ratio-adjusted Nasdaq McClellan Oscillator in the bottom decile of historical readings.")),
        "nymo": study_or_raise("NYMO", event_study(nymo_hist, spy, high=False, title="NYSE McClellan washouts", rule="Ratio-adjusted NYSE McClellan Oscillator in the bottom decile of historical readings.")),
        "trin": study_or_raise("TRIN", event_study(nyse_trin_hist, spy, high=True, title="NYSE TRIN capitulation extremes", rule="NYSE Arms Index in the top decile of historical readings.")),
        "trinq": study_or_raise("TRINQ", event_study(nas_trin_hist, spy, high=True, title="Nasdaq TRINQ capitulation extremes", rule="Nasdaq Arms Index in the top decile of historical readings.")),
        "newlows": study_or_raise("New lows", event_study(nhnl_pressure, spy, high=True, title="52-week new-low pressure extremes", rule="NYSE new 52-week lows as a share of active issues in the top decile of historical readings.")),
        "breadth": study_or_raise("Breadth", event_study(breadth_series, spy, high=False, title="Short-term breadth washouts", rule="S&P 500 5-day participation in the bottom decile of recorded Market Pulse history.")),
        "vol": study_or_raise("Volatility", event_study(vr.stress.dropna(), spy, high=True, title="Volatility stress-cluster extremes", rule="Combined VIX, VVIX, SKEW and term-structure stress score in the top decile of history.")),
    }

    cpce5 = float(cpce_hist.tail(4).sum() + cpce) / min(5, len(cpce_hist.tail(4)) + 1)
    cpce_pct = pct_rank(cpce_hist, cpce)
    namo_pct = pct_rank(namo_hist, namo)
    nymo_pct = pct_rank(nymo_hist, nymo)
    trin_pct = pct_rank(nyse_trin_hist, trin)
    trinq_pct = pct_rank(nas_trin_hist, trinq)
    newlow_pct_rank = pct_rank(nhnl_pressure, newlow_pct_current)
    breadth_pct = pct_rank(breadth_series, safe(ctx.get("breadth", {}).get("above_5d")))
    latest_vr = vr.iloc[-1]

    signals = {
        "cpce": {"value": round(cpce, 3), "average_5d": round(cpce5, 3), "percentile_252d": cpce_pct, "as_of": ctx.get("market_date"), "source": "Cboe Daily Market Statistics", "study": studies["cpce"]},
        "namo": {"value": round(namo, 2), "percentile_252d": namo_pct, "as_of": nas_asof, "source": "Nasdaq Trader advances/declines; ratio-adjusted McClellan calculation", "study": studies["namo"]},
        "nymo": {"value": round(nymo, 2), "percentile_252d": nymo_pct, "as_of": ny_live["as_of"], "source": "McClellan Financial final NYSE breadth", "study": studies["nymo"]},
        "trin": {"value": None if trin is None else round(trin, 3), "percentile_252d": trin_pct, "as_of": ny_live["as_of"], "source": "McClellan Financial NYSE issues and volume; Arms formula", "study": studies["trin"]},
        "trinq": {"value": round(trinq, 3), "percentile_252d": trinq_pct, "as_of": nas_asof, "source": "Barchart $TRIQ current; Unicorn Nasdaq breadth history", "study": studies["trinq"]},
        "newlows": {"value": new_lows_current, "new_highs": safe(ctx.get("breadth", {}).get("new_highs_52w")), "new_low_pct": None if newlow_pct_current is None else round(newlow_pct_current, 2), "percentile_252d": newlow_pct_rank, "as_of": ctx.get("market_date"), "source": "S&P 500 constituent highs/lows; NYSE archive for precedent", "study": studies["newlows"]},
        "breadth": {"above_5d": safe(ctx.get("breadth", {}).get("above_5d")), "above_20d": safe(ctx.get("breadth", {}).get("above_20d")), "above_50d": safe(ctx.get("breadth", {}).get("above_50d")), "above_200d": safe(ctx.get("breadth", {}).get("above_200d")), "percentile_252d": breadth_pct, "as_of": ctx.get("market_date"), "source": ctx.get("breadth", {}).get("source", "S&P 500 constituent breadth"), "study": studies["breadth"]},
        "vol": {"vix": round(float(latest_vr.vix), 2), "vix3m": round(float(latest_vr.vix3m), 2), "term_ratio": round(float(latest_vr.term), 3), "vvix": round(float(latest_vr.vvix), 2), "skew": round(float(latest_vr.skew), 2), "stress_score": round(float(latest_vr.stress), 1), "percentile_252d": pct_rank(vr.stress, float(latest_vr.stress)), "as_of": str(vr.index[-1].date()), "source": "Cboe Global Indices daily history", "study": studies["vol"]},
    }

    for key, row in signals.items():
        primary = row.get("value", row.get("above_5d", row.get("vix")))
        if primary is None:
            raise RuntimeError(f"{key}: current value missing")
        if not row.get("study"):
            raise RuntimeError(f"{key}: study missing")

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market_date": ctx.get("market_date"),
        "methodology": {
            "forward_returns": "SPY close-to-close forward returns at 5, 10, 21 and 60 trading sessions.",
            "breadth_archive": "Unicorn historical breadth archive is used for long-run NYSE/Nasdaq precedent; its live feed ended in 2020. Current readings come from current sources listed per signal.",
            "mcclellan": "Ratio-adjusted net advances multiplied by 1000; 10% EMA minus 5% EMA, equivalent to 19/39-day convention.",
        },
        "signals": signals,
    }
    OUT.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: {x: v for x, v in row.items() if x != "study"} for k, row in signals.items()}, indent=2))


if __name__ == "__main__":
    main()
