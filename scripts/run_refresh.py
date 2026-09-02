#!/usr/bin/env python3
"""Stable benchmark-price adapter for the seven-signal builder.

FRED publishes the S&P 500 daily close as a machine-readable CSV. The series is
used only for forward-return event studies. Individual signal readings retain
their own listed sources.
"""
import io

import pandas as pd

import update_extremes as builder


def fred_sp500_history():
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500"
    r = builder.requests.get(url, headers=builder.UA, timeout=45)
    r.raise_for_status()
    df = pd.read_csv(io.BytesIO(r.content))
    cols = {str(c).strip().lower(): c for c in df.columns}
    date_col = cols.get("observation_date") or cols.get("date")
    value_col = cols.get("sp500") or cols.get("value")
    if date_col is None or value_col is None:
        raise RuntimeError(f"FRED SP500 columns not recognized: {list(df.columns)}")
    s = pd.Series(
        pd.to_numeric(df[value_col], errors="coerce").values,
        index=pd.to_datetime(df[date_col], errors="coerce"),
        dtype="float64",
    ).dropna().sort_index()
    if len(s) < 1000:
        raise RuntimeError("FRED SP500 history too short")
    return s[~s.index.duplicated(keep="last")]


if __name__ == "__main__":
    builder.spy_history = fred_sp500_history
    builder.main()
