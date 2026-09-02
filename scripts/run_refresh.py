#!/usr/bin/env python3
"""Stable runtime adapters for the seven-signal builder.

A versioned public SPY daily dataset is used for historical forward-return
studies. The legacy Unicorn breadth archive currently presents an expired TLS
certificate; certificate verification is disabled for that static archive only.
All live market-data hosts retain normal TLS verification.
"""
import io
import warnings
from datetime import datetime, timezone

import pandas as pd
import urllib3

import update_extremes as builder

_ORIGINAL_GET = builder.get


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


if __name__ == "__main__":
    builder.spy_history = github_spy_history
    builder.get = source_get
    builder.read_unicorn_series = archive_series
    builder.nasdaq_daily = official_nasdaq_daily
    builder.main()
