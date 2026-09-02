#!/usr/bin/env python3
"""Stable benchmark-price adapter for the seven-signal builder.

A versioned public SPY daily dataset is used for historical forward-return
studies. Keeping the study benchmark on GitHub avoids browser gates and rate
limits in unattended Actions runs. Individual signal readings retain their own
listed market-data sources.
"""
import io

import pandas as pd

import update_extremes as builder


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


if __name__ == "__main__":
    builder.spy_history = github_spy_history
    builder.main()
