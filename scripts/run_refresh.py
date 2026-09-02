#!/usr/bin/env python3
"""Buyer-ready runtime adapters for the seven-signal Market Pulse builder.

Adds:
- independent historical extreme episodes instead of counting every consecutive day
- forward return, maximum drawdown, and maximum favorable excursion by horizon
- three independently explainable volatility studies: term structure, VVIX, SKEW
- proprietary Market State / Extreme -> Confirmation -> Trigger synthesis
- a daily What Changed feed based on the prior committed signal snapshot
"""
from __future__ import annotations

import io
import json
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import urllib3

import update_extremes as builder

_ORIGINAL_GET = builder.get
_ORIGINAL_LOCAL_FRAMES = builder.local_frames
_ORIGINAL_SERIES_SKEW = pd.Series.skew


def github_spy_history():
    url = "https://raw.githubusercontent.com/Setooooo/etf-insight/master/data/raw/SPY.csv"
    r = builder.requests.get(url, headers=builder.UA, timeout=45)
    r.raise_for_status()
    df = pd.read_csv(io.BytesIO(r.content))
    cols = {str(c).strip().lower(): c for c in df.columns}
    date_col = cols.get("date")
    value_col = cols.get("adj close") or cols.get("close")
    if date_col is None or value_col is None:
        raise RuntimeError(f"GitHub SPY columns not recognized: {list(df.columns)}")
    s = pd.Series(
        pd.to_numeric(df[value_col], errors="coerce").values,
        index=pd.to_datetime(df[date_col], errors="coerce"),
        dtype="float64",
    ).dropna().sort_index()
    if len(s) < 5000:
        raise RuntimeError("Versioned SPY history too short")
    return s[~s.index.duplicated(keep="last")]


def source_get(url, timeout=30):
    if "unicorn.us.com" not in url:
        return _ORIGINAL_GET(url, timeout=timeout)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = builder.requests.get(url, headers=builder.UA, timeout=timeout, verify=False)
    r.raise_for_status()
    return r


def parse_archive_dates(values):
    raw = pd.Series(values).astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    compact = raw.str.fullmatch(r"\d{8}")
    dates = pd.Series(pd.NaT, index=raw.index, dtype="datetime64[ns]")
    if compact.any():
        dates.loc[compact] = pd.to_datetime(raw.loc[compact], format="%Y%m%d", errors="coerce")
    if (~compact).any():
        dates.loc[~compact] = pd.to_datetime(raw.loc[~compact], errors="coerce")
    return dates


def archive_series(url):
    df = pd.read_csv(io.StringIO(source_get(url, timeout=45).text), header=None, comment="#")
    if df.shape[1] < 2:
        raise RuntimeError(f"Breadth archive series invalid: {url}")
    dates = parse_archive_dates(df.iloc[:, 0])
    vals = pd.to_numeric(df.iloc[:, -1], errors="coerce")
    s = pd.Series(vals.values, index=dates).dropna().sort_index()
    s = s[~s.index.isna()]
    if len(s) < 100:
        raise RuntimeError(f"Breadth archive series too short after date parse: {url}")
    return s[~s.index.duplicated(keep="last")]


def official_nasdaq_daily():
    year = datetime.now(timezone.utc).year
    url = f"https://www.nasdaqtrader.com/dynamic/dailyfiles/daily{year}.csv"
    df = pd.read_csv(io.BytesIO(source_get(url, timeout=45).content))
    cols = {str(c).strip().lower(): c for c in df.columns}
    date_col = cols.get("date")
    adv_col = cols.get("advances")
    dec_col = cols.get("declines")
    if date_col is None or adv_col is None or dec_col is None:
        raise RuntimeError(f"Nasdaq official breadth columns not recognized: {list(df.columns)}")
    out = pd.DataFrame({
        "date": pd.to_datetime(df[date_col], errors="coerce"),
        "adv": pd.to_numeric(df[adv_col], errors="coerce"),
        "dec": pd.to_numeric(df[dec_col], errors="coerce"),
    }).dropna().set_index("date").sort_index()
    if len(out) < 40:
        raise RuntimeError("Nasdaq official current-year breadth history too short")
    return out


def parse_put_call_csv(text):
    rows = []
    for line in text.splitlines():
        parts = [x.strip().strip('"') for x in line.split(",")]
        if len(parts) < 2:
            continue
        date = pd.to_datetime(parts[0], errors="coerce")
        if pd.isna(date):
            continue
        nums = []
        for token in parts[1:]:
            try:
                nums.append(float(token.replace(",", "")))
            except (TypeError, ValueError):
                continue
        if not nums:
            continue
        ratio = nums[-1]
        if 0.05 <= ratio <= 10:
            rows.append((date.normalize(), ratio))
    if not rows:
        raise RuntimeError("Cboe equity put/call CSV parsed no observations")
    s = pd.Series({d: v for d, v in rows}, dtype="float64").sort_index()
    return s[~s.index.duplicated(keep="last")]


def cboe_equity_pc_history():
    urls = [
        "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/equitypc.csv",
        "https://cdn.cboe.com/api/global/us_indices/daily_prices/EQUITY_PC_RATIOS.csv",
    ]
    pieces = []
    for url in urls:
        try:
            pieces.append(parse_put_call_csv(source_get(url, timeout=45).text))
        except Exception as exc:
            print(f"CPCE history source warning: {url}: {exc}")
    if not pieces:
        raise RuntimeError("No Cboe equity put/call history source available")
    s = pd.concat(pieces).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    if len(s) < 1000:
        raise RuntimeError(f"Cboe equity put/call history too short: {len(s)}")
    return s


def long_history_frames(hist):
    br, market, local_pc = _ORIGINAL_LOCAL_FRAMES(hist)
    pc = cboe_equity_pc_history()
    if not local_pc.empty and "value" in local_pc:
        tail = pd.to_numeric(local_pc["value"], errors="coerce").dropna()
        pc = pd.concat([pc, tail]).sort_index()
        pc = pc[~pc.index.duplicated(keep="last")]
    return br, market, pd.DataFrame({"value": pc})


def series_skew_column(self):
    if "skew" in self.index:
        return self["skew"]
    return _ORIGINAL_SERIES_SKEW.__get__(self, pd.Series)


def _episode_dates(series: pd.Series, mask: pd.Series, min_gap_sessions: int = 5):
    positions = np.flatnonzero(mask.values)
    chosen = []
    last = -10_000
    for pos in positions:
        if pos - last >= min_gap_sessions:
            chosen.append(series.index[pos])
            last = pos
    return chosen


def episode_event_study(series: pd.Series, spy: pd.Series, *, high: bool, title: str, rule: str, quantile=.90):
    """Event study using independent episodes and path-risk statistics."""
    s = pd.to_numeric(series, errors="coerce").dropna().sort_index()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    if len(s) < 40:
        return None
    threshold = float(s.quantile(quantile if high else 1 - quantile))
    mask = s >= threshold if high else s <= threshold
    event_dates = _episode_dates(s, mask, min_gap_sessions=5)
    if len(event_dates) < 5:
        return None

    px = pd.to_numeric(spy, errors="coerce").dropna().sort_index()
    px.index = pd.to_datetime(px.index).tz_localize(None)
    loc = {d: i for i, d in enumerate(px.index)}
    horizons = {}
    usable_dates = []

    for h in builder.HORIZONS:
        rets, drawdowns, excursions = [], [], []
        for d in event_dates:
            i = loc.get(d)
            if i is None or i + h >= len(px):
                continue
            start = float(px.iloc[i])
            path = px.iloc[i:i + h + 1].astype(float)
            rets.append(100 * (float(path.iloc[-1]) / start - 1))
            drawdowns.append(100 * (float(path.min()) / start - 1))
            excursions.append(100 * (float(path.max()) / start - 1))
            if h == 21:
                usable_dates.append(str(d.date()))
        st = builder.stats(rets)
        if not st:
            continue
        st["median_max_drawdown"] = round(float(np.median(drawdowns)), 3)
        st["median_max_favorable"] = round(float(np.median(excursions)), 3)
        horizons[str(h)] = st

    if not horizons:
        return None
    return {
        "title": title,
        "rule": rule,
        "threshold": round(threshold, 4),
        "direction": "high" if high else "low",
        "historical_sample": len(event_dates),
        "episode_method": "Independent episodes separated by at least 5 signal sessions.",
        "horizons": horizons,
        "prior_dates": usable_dates[-12:][::-1],
    }


def enrich_volatility_family():
    out = builder.OUT
    payload = json.loads(out.read_text())
    vol = payload["signals"]["vol"]
    spy = github_spy_history()

    vix = builder.cboe_series("VIX")
    vix3m = builder.cboe_series("VIX3M")
    vvix = builder.cboe_series("VVIX")
    skew = builder.cboe_series("SKEW")
    frame = pd.concat({"vix": vix, "vix3m": vix3m, "vvix": vvix, "skew": skew}, axis=1).dropna()
    frame["term"] = frame["vix"] / frame["vix3m"]
    latest = frame.iloc[-1]

    term_study = builder.require_study(
        "VIX term structure",
        episode_event_study(
            frame["term"], spy, high=True,
            title="VIX term-structure stress",
            rule="VIX/VIX3M ratio in the top decile of history. Higher ratios mean near-term fear is unusually urgent; readings above 1.00 indicate inversion.",
        ),
    )
    vvix_study = builder.require_study(
        "VVIX",
        episode_event_study(
            frame["vvix"], spy, high=True,
            title="VVIX fear-of-fear extremes",
            rule="VVIX in the top decile of history, indicating unusually expensive volatility hedging.",
        ),
    )
    skew_study = builder.require_study(
        "SKEW",
        episode_event_study(
            frame["skew"], spy, high=True,
            title="SKEW tail-risk extremes",
            rule="Cboe SKEW in the top decile of history, indicating unusually elevated pricing for large downside moves.",
        ),
    )

    vol.update({
        "term_ratio": round(float(latest["term"]), 3),
        "term_percentile_252d": builder.pct_rank(frame["term"], float(latest["term"])),
        "vvix_percentile_252d": builder.pct_rank(frame["vvix"], float(latest["vvix"])),
        "skew_percentile_252d": builder.pct_rank(frame["skew"], float(latest["skew"])),
        "term_study": term_study,
        "vvix_study": vvix_study,
        "skew_study": skew_study,
    })
    payload["methodology"]["volatility_family"] = (
        "Volatility Regime uses VIX/VIX3M term structure, VVIX and SKEW as three separate signals. Raw VIX is supporting context only."
    )
    out.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def _pct(row, key="percentile_252d", default=50.0):
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def derive_market_state(payload, previous):
    s = payload["signals"]
    cpce = _pct(s["cpce"])
    vol = s["vol"]
    vol_peak = max(_pct(vol, "term_percentile_252d"), _pct(vol, "vvix_percentile_252d"), _pct(vol, "skew_percentile_252d"))
    nymo = _pct(s["nymo"])
    namo = _pct(s["namo"])
    breadth = _pct(s["breadth"])
    newlows = _pct(s["newlows"])
    trin = _pct(s["trin"])
    trinq = _pct(s["trinq"])

    fear_score = max(cpce, vol_peak)
    breadth_stress = max(100 - nymo, 100 - namo, 100 - breadth, newlows)
    capitulation_score = max(trin, trinq)

    if fear_score >= 90:
        fear_label = "Extreme"
    elif fear_score >= 75:
        fear_label = "Elevated"
    else:
        fear_label = "Contained"

    if breadth_stress >= 97.5:
        internals_label = "Severe washout"
    elif breadth_stress >= 90:
        internals_label = "Washout"
    elif breadth_stress >= 75:
        internals_label = "Weak"
    else:
        internals_label = "Healthy"

    if capitulation_score >= 90:
        capitulation_label = "Confirmed"
    elif capitulation_score >= 75:
        capitulation_label = "Building"
    else:
        capitulation_label = "Not confirmed"

    extreme = breadth_stress >= 90 or fear_score >= 90 or capitulation_score >= 90
    confirmation = sum([
        breadth_stress >= 90,
        fear_score >= 75,
        newlows >= 75,
        capitulation_score >= 75,
    ]) >= 2

    prev_signals = (previous or {}).get("signals", {})
    prev_nymo = _pct(prev_signals.get("nymo", {})) if prev_signals else None
    prev_breadth = _pct(prev_signals.get("breadth", {})) if prev_signals else None
    trigger = False
    if prev_nymo is not None and prev_breadth is not None:
        trigger = (nymo > prev_nymo + 5) and (breadth > prev_breadth + 5)

    if breadth_stress >= 97.5 and not trigger:
        state = "Breadth Washout"
        summary = "Market internals are severely stretched, but a reversal trigger has not been confirmed yet."
    elif breadth_stress >= 90 and trigger:
        state = "Reversal Setup"
        summary = "Breadth reached a washout and has begun to recover, creating a potential reversal setup."
    elif capitulation_score >= 90:
        state = "Capitulation"
        summary = "Selling pressure has reached panic-like levels across price and volume breadth."
    elif fear_score >= 90 and breadth_stress < 75:
        state = "Fear Extreme"
        summary = "Options markets are unusually defensive, but broad market internals have not broken down."
    elif breadth_stress >= 75:
        state = "Early Stress"
        summary = "Participation is deteriorating beneath the indexes, but the market has not reached a full washout."
    elif min(nymo, namo, breadth) >= 75:
        state = "Breadth Thrust"
        summary = "Participation and breadth momentum are unusually strong across the market."
    else:
        state = "Healthy Trend"
        summary = "No major internal stress regime is dominating the market right now."

    payload["market_state"] = {
        "name": state,
        "summary": summary,
        "dimensions": {
            "fear": {"label": fear_label, "score": round(fear_score, 1)},
            "internals": {"label": internals_label, "score": round(breadth_stress, 1)},
            "capitulation": {"label": capitulation_label, "score": round(capitulation_score, 1)},
        },
        "setup": {
            "extreme": {"confirmed": bool(extreme), "copy": "A historically unusual condition is present." if extreme else "No major historical extreme is present."},
            "confirmation": {"confirmed": bool(confirmation), "copy": "Independent signal families agree." if confirmation else "Independent confirmation is still limited."},
            "trigger": {"confirmed": bool(trigger), "copy": "Breadth momentum has started to recover." if trigger else "A reversal trigger is not confirmed yet."},
        },
    }


def _primary_value(key, row):
    if key == "breadth":
        return row.get("above_5d")
    if key == "vol":
        return row.get("term_ratio")
    return row.get("value")


def derive_changes(payload, previous):
    labels = {
        "cpce": "Options fear",
        "namo": "Nasdaq breadth",
        "nymo": "NYSE breadth",
        "trin": "NYSE selling pressure",
        "trinq": "Nasdaq selling pressure",
        "newlows": "New-low pressure",
        "breadth": "Short-term participation",
        "vol": "Volatility term structure",
    }
    changes = []
    prior = (previous or {}).get("signals", {})
    for key, row in payload["signals"].items():
        if key not in prior:
            continue
        cur = _primary_value(key, row)
        old = _primary_value(key, prior[key])
        try:
            cur_f, old_f = float(cur), float(old)
        except (TypeError, ValueError):
            continue
        delta = cur_f - old_f
        if abs(delta) < (0.01 if key in {"cpce", "trin", "trinq", "vol"} else 1.0):
            continue
        direction = "rose" if delta > 0 else "fell"
        if key == "breadth":
            copy = f"{labels[key]} {direction} from {old_f:.0f}% to {cur_f:.0f}% above the 5-day trend."
        elif key == "vol":
            copy = f"{labels[key]} {direction} from {old_f:.2f} to {cur_f:.2f}."
        else:
            copy = f"{labels[key]} {direction} from {old_f:.2f} to {cur_f:.2f}."
        changes.append({"signal": key, "headline": labels[key], "detail": copy, "magnitude": round(abs(delta), 3)})
    changes.sort(key=lambda x: x["magnitude"], reverse=True)
    if not changes:
        changes = [{"signal": "market", "headline": "No major state change", "detail": "The core signal set is broadly unchanged from the prior completed snapshot.", "magnitude": 0}]
    payload["what_changed"] = changes[:3]


def finalize_product_layer(previous):
    payload = json.loads(builder.OUT.read_text())
    derive_market_state(payload, previous)
    derive_changes(payload, previous)
    payload["methodology"]["event_studies"] = (
        "Historical studies use independent extreme episodes separated by at least five signal sessions and report forward return, median maximum drawdown, and median maximum favorable excursion."
    )
    builder.OUT.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    previous_payload = None
    if builder.OUT.exists():
        try:
            previous_payload = json.loads(builder.OUT.read_text())
        except Exception:
            previous_payload = None

    builder.spy_history = github_spy_history
    builder.get = source_get
    builder.read_unicorn_series = archive_series
    builder.nasdaq_daily = official_nasdaq_daily
    builder.local_frames = long_history_frames
    builder.event_study = episode_event_study
    pd.Series.skew = property(series_skew_column)

    builder.main()
    enrich_volatility_family()
    finalize_product_layer(previous_payload)
