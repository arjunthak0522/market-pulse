#!/usr/bin/env python3
"""Stable runtime adapters for the seven-signal builder.

A versioned public SPY daily dataset is used for historical forward-return
studies. The legacy Unicorn breadth archive currently presents an expired TLS
certificate; certificate verification is disabled for that static archive only.
All live market-data hosts retain normal TLS verification.

The volatility family is intentionally decomposed into three independently
explainable signals: VIX term structure, VVIX and SKEW. Each receives its own
historical rank and forward-return study after the core dataset is built.
"""
import io
import json
import warnings
from datetime import datetime, timezone

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
    """Parse Cboe put/call CSVs with preambles/header changes across eras."""
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


def enrich_volatility_family():
    """Attach separate ranks and studies for term structure, VVIX and SKEW."""
    out = builder.OUT
    payload = json.loads(out.read_text())
    vol = payload["signals"]["vol"]
    spy = github_spy_history()

    vix = builder.cboe_series("VIX")
    vix3m = builder.cboe_series("VIX3M")
    vvix = builder.cboe_series("VVIX")
    skew = builder.cboe_series("SKEW")
    frame = pd.concat({"vix": vix, "vix3m": vix3m, "vvix": vvix, "skew": skew}, axis=1).dropna()
    frame["term"] = frame.vix / frame.vix3m
    latest = frame.iloc[-1]

    term_study = builder.require_study(
        "VIX term structure",
        builder.event_study(
            frame.term,
            spy,
            high=True,
            title="VIX term-structure stress",
            rule="VIX/VIX3M ratio in the top decile of history. Higher ratios mean near-term fear is unusually urgent; readings above 1.00 indicate inversion.",
        ),
    )
    vvix_study = builder.require_study(
        "VVIX",
        builder.event_study(
            frame.vvix,
            spy,
            high=True,
            title="VVIX fear-of-fear extremes",
            rule="VVIX in the top decile of history, indicating unusually expensive volatility hedging.",
        ),
    )
    skew_study = builder.require_study(
        "SKEW",
        builder.event_study(
            frame.skew,
            spy,
            high=True,
            title="SKEW tail-risk extremes",
            rule="Cboe SKEW in the top decile of history, indicating unusually elevated pricing for large downside moves.",
        ),
    )

    vol.update({
        "term_ratio": round(float(latest.term), 3),
        "term_percentile_252d": builder.pct_rank(frame.term, float(latest.term)),
        "vvix_percentile_252d": builder.pct_rank(frame.vvix, float(latest.vvix)),
        "skew_percentile_252d": builder.pct_rank(frame.skew, float(latest.skew)),
        "term_study": term_study,
        "vvix_study": vvix_study,
        "skew_study": skew_study,
    })
    payload["methodology"]["volatility_family"] = (
        "Volatility Regime uses VIX/VIX3M term structure, VVIX and SKEW as three separate signals. "
        "Raw VIX is supporting context only."
    )
    out.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    builder.spy_history = github_spy_history
    builder.get = source_get
    builder.read_unicorn_series = archive_series
    builder.nasdaq_daily = official_nasdaq_daily
    builder.local_frames = long_history_frames
    pd.Series.skew = property(series_skew_column)
    builder.main()
    enrich_volatility_family()
