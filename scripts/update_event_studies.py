#!/usr/bin/env python3
"""Precompute historical event studies for Market Pulse.

V1 covers SPY / QQQ price and momentum events plus VIX regime events. The
browser consumes the generated JSON and never recomputes the full history.
All horizons are trading-session offsets in the downloaded daily series.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "event_studies.json"
START = "1999-01-01"
HORIZONS = (1, 2, 3, 5, 10, 21, 63)
PATH_HORIZONS = (5, 10, 21, 63)
THRESHOLDS = (0.01, 0.02, 0.03, 0.05)


def safe_num(v):
    if v is None or pd.isna(v):
        return None
    x = float(v)
    return x if np.isfinite(x) else None


def pct(v, digits=4):
    x = safe_num(v)
    return None if x is None else round(100 * x, digits)


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    d = close.diff()
    gains = d.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    losses = (-d.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gains / losses.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def rolling_percentile(series: pd.Series, window: int = 252, min_periods: int = 100) -> pd.Series:
    def rank_last(a):
        if not len(a):
            return np.nan
        return 100 * np.mean(a <= a[-1])
    return series.rolling(window, min_periods=min_periods).apply(rank_last, raw=True)


def consecutive(mask: pd.Series, sessions: int) -> pd.Series:
    return mask.rolling(sessions).sum().eq(sessions)


def crossing_above(series: pd.Series, level: float) -> pd.Series:
    return series.gt(level) & series.shift(1).le(level)


def crossing_below(series: pd.Series, level: float) -> pd.Series:
    return series.lt(level) & series.shift(1).ge(level)


def first_cross_after_reset(series: pd.Series, level: float, reset_sessions: int, direction: str) -> pd.Series:
    if direction == "above":
        reset = series.shift(1).le(level).rolling(reset_sessions).sum().eq(reset_sessions)
        return crossing_above(series, level) & reset
    reset = series.shift(1).ge(level).rolling(reset_sessions).sum().eq(reset_sessions)
    return crossing_below(series, level) & reset


def cooldown(mask: pd.Series, sessions: int) -> pd.Series:
    """Keep the first event, then require `sessions` observations before another."""
    out = pd.Series(False, index=mask.index)
    last = -10**9
    for i, hit in enumerate(mask.fillna(False).to_numpy(dtype=bool)):
        if hit and i - last > sessions:
            out.iloc[i] = True
            last = i
    return out


def compound_transition(*conditions: Callable[[pd.DataFrame], pd.Series]) -> Callable[[pd.DataFrame], pd.Series]:
    """Trigger once when all supplied conditions become true together."""
    def detect(df: pd.DataFrame) -> pd.Series:
        active = pd.Series(True, index=df.index)
        for condition in conditions:
            active &= condition(df).fillna(False)
        return active & ~active.shift(1, fill_value=False)
    return detect


@dataclass(frozen=True)
class SignalSpec:
    signal_id: str
    title: str
    symbol_scope: tuple[str, ...]
    rule: str
    detector: Callable[[pd.DataFrame], pd.Series]
    priority: int = 50
    cooldown_sessions: int = 0
    category: str = "Price / momentum"
    conditions: tuple[str, ...] = ()


def ma_cross(period: int, direction: str) -> Callable[[pd.DataFrame], pd.Series]:
    def detect(df: pd.DataFrame) -> pd.Series:
        ma = df[f"ma{period}"]
        return crossing_above(df.close - ma, 0) if direction == "above" else crossing_below(df.close - ma, 0)
    return detect


def distance_cross(period: int, threshold_pct: float, direction: str) -> Callable[[pd.DataFrame], pd.Series]:
    def detect(df: pd.DataFrame) -> pd.Series:
        s = df[f"dist_ma{period}"]
        return crossing_above(s, threshold_pct) if direction == "above" else crossing_below(s, threshold_pct)
    return detect


def daily_move(threshold: float, direction: str) -> Callable[[pd.DataFrame], pd.Series]:
    def detect(df: pd.DataFrame) -> pd.Series:
        r = df.close.pct_change()
        return r.ge(threshold) if direction == "up" else r.le(-threshold)
    return detect


def multi_move(sessions: int, threshold: float, direction: str) -> Callable[[pd.DataFrame], pd.Series]:
    def detect(df: pd.DataFrame) -> pd.Series:
        r = df.close.pct_change(sessions)
        return r.ge(threshold) if direction == "up" else r.le(-threshold)
    return detect


def gap_move(threshold: float, direction: str) -> Callable[[pd.DataFrame], pd.Series]:
    def detect(df: pd.DataFrame) -> pd.Series:
        gap = df.open / df.close.shift(1) - 1
        return gap.ge(threshold) if direction == "up" else gap.le(-threshold)
    return detect


def drawdown_cross(lookback: int, threshold: float) -> Callable[[pd.DataFrame], pd.Series]:
    def detect(df: pd.DataFrame) -> pd.Series:
        peak = df.close.shift(1).rolling(lookback).max()
        drawdown = df.close / peak - 1
        return crossing_below(drawdown, -threshold)
    return detect


def run_streak(sessions: int, direction: str) -> Callable[[pd.DataFrame], pd.Series]:
    def detect(df: pd.DataFrame) -> pd.Series:
        r = df.close.diff()
        now = consecutive(r.gt(0) if direction == "up" else r.lt(0), sessions)
        prev = consecutive(r.gt(0) if direction == "up" else r.lt(0), sessions + 1)
        return now & ~prev
    return detect


def vix_cross(level: float, direction: str) -> Callable[[pd.DataFrame], pd.Series]:
    def detect(df: pd.DataFrame) -> pd.Series:
        s = df.vix
        return crossing_above(s, level) if direction == "above" else crossing_below(s, level)
    return detect


def signal_catalog() -> list[SignalSpec]:
    specs = [
        SignalSpec("rsi_cross_above_70", "RSI breakout above 70", ("SPY", "QQQ"), "RSI(14) crosses from <=70 to >70.", lambda d: crossing_above(d.rsi14, 70), 90),
        SignalSpec("rsi_cross_above_70_reset20", "RSI breakout after long reset", ("SPY", "QQQ"), "RSI(14) crosses >70 after remaining <=70 for at least 20 consecutive trading sessions.", lambda d: first_cross_after_reset(d.rsi14, 70, 20, "above"), 100),
        SignalSpec("rsi_cross_below_30", "RSI breakdown below 30", ("SPY", "QQQ"), "RSI(14) crosses from >=30 to <30.", lambda d: crossing_below(d.rsi14, 30), 90),
        SignalSpec("rsi_exit_oversold", "RSI exits oversold", ("SPY", "QQQ"), "RSI(14) crosses from <=30 to >30.", lambda d: crossing_above(d.rsi14, 30), 95),
        SignalSpec("rsi_exit_overbought", "RSI exits overbought", ("SPY", "QQQ"), "RSI(14) crosses from >=70 to <70.", lambda d: crossing_below(d.rsi14, 70), 95),
        SignalSpec("rsi_overbought_5", "RSI overbought for 5 sessions", ("SPY", "QQQ"), "RSI(14) remains >70 for 5 consecutive trading sessions; triggers once on session 5.", lambda d: consecutive(d.rsi14.gt(70), 5) & ~consecutive(d.rsi14.gt(70), 6), 70),
        SignalSpec("rsi_oversold_5", "RSI oversold for 5 sessions", ("SPY", "QQQ"), "RSI(14) remains <30 for 5 consecutive trading sessions; triggers once on session 5.", lambda d: consecutive(d.rsi14.lt(30), 5) & ~consecutive(d.rsi14.lt(30), 6), 70),
    ]
    for period in (20, 50, 200):
        specs.extend([
            SignalSpec(f"price_cross_above_ma{period}", f"Reclaims {period}DMA", ("SPY", "QQQ"), f"Adjusted close crosses from at/below to above the {period}-day moving average.", ma_cross(period, "above"), 85),
            SignalSpec(f"price_cross_below_ma{period}", f"Loses {period}DMA", ("SPY", "QQQ"), f"Adjusted close crosses from at/above to below the {period}-day moving average.", ma_cross(period, "below"), 85),
            SignalSpec(f"distance_ma{period}_below_2", f"Moves 2% below {period}DMA", ("SPY", "QQQ"), f"Distance from the {period}-day moving average crosses from >=-2% to <-2%.", distance_cross(period, -2, "below"), 55),
            SignalSpec(f"distance_ma{period}_above_2", f"Moves 2% above {period}DMA", ("SPY", "QQQ"), f"Distance from the {period}-day moving average crosses from <=+2% to >+2%.", distance_cross(period, 2, "above"), 55),
        ])
    specs.extend([
        SignalSpec("golden_cross", "50DMA crosses above 200DMA", ("SPY", "QQQ"), "50-day moving average crosses from at/below to above the 200-day moving average.", lambda d: crossing_above(d.ma50 - d.ma200, 0), 88),
        SignalSpec("death_cross", "50DMA crosses below 200DMA", ("SPY", "QQQ"), "50-day moving average crosses from at/above to below the 200-day moving average.", lambda d: crossing_below(d.ma50 - d.ma200, 0), 88),
        SignalSpec("new_52w_high", "New 52-week high", ("SPY", "QQQ"), "Adjusted close exceeds the highest adjusted close of the prior 252 trading sessions.", lambda d: d.close.gt(d.close.shift(1).rolling(252).max()), 78, 10),
        SignalSpec("new_52w_low", "New 52-week low", ("SPY", "QQQ"), "Adjusted close falls below the lowest adjusted close of the prior 252 trading sessions.", lambda d: d.close.lt(d.close.shift(1).rolling(252).min()), 78, 10),
        SignalSpec("daily_gain_2", "Large daily rally", ("SPY", "QQQ"), "One-session adjusted-close return is >= +2%.", daily_move(.02, "up"), 65, 2),
        SignalSpec("daily_decline_2", "Large daily selloff", ("SPY", "QQQ"), "One-session adjusted-close return is <= -2%.", daily_move(.02, "down"), 80, 2),
        SignalSpec("three_day_gain_3", "Three-day rally >3%", ("SPY", "QQQ"), "Three-session adjusted-close return is >= +3%.", multi_move(3, .03, "up"), 60, 3),
        SignalSpec("three_day_decline_3", "Three-day selloff >3%", ("SPY", "QQQ"), "Three-session adjusted-close return is <= -3%.", multi_move(3, .03, "down"), 78, 3),
        SignalSpec("three_up_days", "Three consecutive up days", ("SPY", "QQQ"), "Adjusted close rises for exactly the first 3 consecutive sessions of an up streak.", run_streak(3, "up"), 45),
        SignalSpec("three_down_days", "Three consecutive down days", ("SPY", "QQQ"), "Adjusted close falls for exactly the first 3 consecutive sessions of a down streak.", run_streak(3, "down"), 55),
        SignalSpec("gap_up_1_5", "Gap up >1.5%", ("SPY", "QQQ"), "Adjusted open is at least 1.5% above the prior adjusted close.", gap_move(.015, "up"), 58, 2),
        SignalSpec("gap_down_1_5", "Gap down >1.5%", ("SPY", "QQQ"), "Adjusted open is at least 1.5% below the prior adjusted close.", gap_move(.015, "down"), 68, 2),
        SignalSpec("drawdown_63d_cross_5", "Drawdown crosses -5%", ("SPY", "QQQ"), "Adjusted close crosses below 5% beneath the highest close of the prior 63 trading sessions.", drawdown_cross(63, .05), 68, 5),
        SignalSpec("drawdown_63d_cross_10", "Drawdown crosses -10%", ("SPY", "QQQ"), "Adjusted close crosses below 10% beneath the highest close of the prior 63 trading sessions.", drawdown_cross(63, .10), 82, 10),
        SignalSpec("vix_cross_above_20", "VIX crosses above 20", ("SPY", "QQQ"), "VIX crosses from <=20 to >20.", vix_cross(20, "above"), 72, category="Volatility"),
        SignalSpec("vix_cross_above_25", "VIX crosses above 25", ("SPY", "QQQ"), "VIX crosses from <=25 to >25.", vix_cross(25, "above"), 80, category="Volatility"),
        SignalSpec("vix_cross_above_30", "VIX crosses above 30", ("SPY", "QQQ"), "VIX crosses from <=30 to >30.", vix_cross(30, "above"), 90, category="Volatility"),
        SignalSpec("vix_falls_below_20", "VIX falls back below 20", ("SPY", "QQQ"), "VIX crosses from >=20 to <20.", vix_cross(20, "below"), 70, category="Volatility"),
        SignalSpec("vix_falls_below_25", "VIX falls back below 25", ("SPY", "QQQ"), "VIX crosses from >=25 to <25.", vix_cross(25, "below"), 72, category="Volatility"),
        SignalSpec("vix_falls_below_30", "VIX falls back below 30", ("SPY", "QQQ"), "VIX crosses from >=30 to <30.", vix_cross(30, "below"), 75, category="Volatility"),
        SignalSpec("vix_one_day_spike_20pct", "VIX one-day spike >20%", ("SPY", "QQQ"), "VIX rises at least 20% in one trading session.", lambda d: d.vix.pct_change().ge(.20), 82, 2, "Volatility"),
        SignalSpec("vix_three_day_spike_30pct", "VIX three-day spike >30%", ("SPY", "QQQ"), "VIX rises at least 30% over three trading sessions.", lambda d: d.vix.pct_change(3).ge(.30), 82, 3, "Volatility"),
        SignalSpec("vix_percentile_cross_90", "VIX enters top decile", ("SPY", "QQQ"), "VIX 252-session rolling percentile crosses from <=90 to >90.", lambda d: crossing_above(d.vix_pct252, 90), 86, 5, "Volatility"),
        SignalSpec("vix_percentile_exit_90", "VIX exits top decile", ("SPY", "QQQ"), "VIX 252-session rolling percentile crosses from >=90 to <90.", lambda d: crossing_below(d.vix_pct252, 90), 74, 5, "Volatility"),
        SignalSpec(
            "compound_oversold_selloff_vix25",
            "Oversold selloff with VIX >25",
            ("SPY", "QQQ"),
            "RSI(14) <35 AND three-session return <=-3% AND VIX >25; triggers only when the full condition first becomes true.",
            compound_transition(lambda d: d.rsi14.lt(35), lambda d: d.close.pct_change(3).le(-.03), lambda d: d.vix.gt(25)),
            92,
            10,
            "Compound",
            ("RSI(14)<35", "3-session return<=-3%", "VIX>25"),
        ),
    ])
    return specs


def prepare(df: pd.DataFrame, vix: pd.Series) -> pd.DataFrame:
    x = df.copy().sort_index()
    x.columns = [str(c).lower() for c in x.columns]
    x = x[["open", "high", "low", "close", "volume"]].dropna(subset=["close", "high", "low"])
    x["rsi14"] = rsi(x.close)
    for p in (20, 50, 200):
        x[f"ma{p}"] = x.close.rolling(p).mean()
        x[f"dist_ma{p}"] = (x.close / x[f"ma{p}"] - 1) * 100
    x["vix"] = vix.reindex(x.index).ffill(limit=3)
    x["vix_pct252"] = rolling_percentile(x.vix, 252, 100)
    return x


def stats(values: list[float]) -> dict:
    a = np.asarray([x for x in values if np.isfinite(x)], dtype=float)
    if not len(a):
        return {"n": 0}
    return {
        "n": int(len(a)),
        "average": pct(a.mean()),
        "median": pct(np.median(a)),
        "positive_rate": round(100 * np.mean(a > 0), 1),
        "negative_rate": round(100 * np.mean(a < 0), 1),
        "best": pct(a.max()),
        "worst": pct(a.min()),
        "p25": pct(np.percentile(a, 25)),
        "p75": pct(np.percentile(a, 75)),
    }


def path_metrics(df: pd.DataFrame, event_positions: list[int], horizon: int) -> dict:
    maes, mfes, hit_times = [], [], {t: [] for t in THRESHOLDS}
    up_hits = {t: 0 for t in THRESHOLDS}
    down_hits = {t: 0 for t in THRESHOLDS}
    down_first = {t: 0 for t in THRESHOLDS}
    up_first = {t: 0 for t in THRESHOLDS}
    ambiguous = {t: 0 for t in THRESHOLDS}
    usable = 0
    for pos in event_positions:
        if pos + horizon >= len(df):
            continue
        base = float(df.close.iloc[pos])
        window = df.iloc[pos + 1 : pos + horizon + 1]
        low_path = window.low.to_numpy(dtype=float) / base - 1
        high_path = window.high.to_numpy(dtype=float) / base - 1
        if not len(low_path):
            continue
        usable += 1
        maes.append(float(np.min(low_path)))
        mfes.append(float(np.max(high_path)))
        for t in THRESHOLDS:
            up_idx = np.flatnonzero(high_path >= t)
            dn_idx = np.flatnonzero(low_path <= -t)
            first_up = int(up_idx[0]) if len(up_idx) else None
            first_dn = int(dn_idx[0]) if len(dn_idx) else None
            if first_up is not None:
                up_hits[t] += 1
                hit_times[t].append(first_up + 1)
            if first_dn is not None:
                down_hits[t] += 1
            if first_dn is not None and (first_up is None or first_dn < first_up):
                down_first[t] += 1
            elif first_up is not None and (first_dn is None or first_up < first_dn):
                up_first[t] += 1
            elif first_up is not None and first_dn is not None and first_up == first_dn:
                ambiguous[t] += 1
    out = {
        "n": usable,
        "median_max_drawdown": pct(np.median(maes)) if maes else None,
        "median_max_rally": pct(np.median(mfes)) if mfes else None,
        "maximum_adverse_excursion": pct(np.min(maes)) if maes else None,
        "maximum_favorable_excursion": pct(np.max(mfes)) if mfes else None,
        "thresholds": {},
    }
    for t in THRESHOLDS:
        key = f"{int(t * 100)}pct"
        out["thresholds"][key] = {
            "reached_up": round(100 * up_hits[t] / usable, 1) if usable else None,
            "reached_down": round(100 * down_hits[t] / usable, 1) if usable else None,
            "downside_hit_first": round(100 * down_first[t] / usable, 1) if usable else None,
            "upside_hit_first": round(100 * up_first[t] / usable, 1) if usable else None,
            "same_day_order_ambiguous": round(100 * ambiguous[t] / usable, 1) if usable else None,
            "median_days_to_up": round(float(np.median(hit_times[t])), 1) if hit_times[t] else None,
        }
    return out


def baseline_positions(df: pd.DataFrame, horizon: int) -> list[int]:
    return list(range(0, max(0, len(df) - horizon)))


def outcome_rows(df: pd.DataFrame, mask: pd.Series) -> tuple[list[dict], list[int]]:
    positions = np.flatnonzero(mask.reindex(df.index, fill_value=False).to_numpy(dtype=bool)).tolist()
    rows = []
    for pos in positions:
        row = {"event_date": str(df.index[pos].date())}
        base = float(df.close.iloc[pos])
        for h in HORIZONS:
            row[f"return_{h}d"] = pct(float(df.close.iloc[pos + h]) / base - 1) if pos + h < len(df) else None
        rows.append(row)
    return rows, positions


def summarize_study(df: pd.DataFrame, positions: list[int]) -> dict:
    horizons = {}
    for h in HORIZONS:
        signal_values = [float(df.close.iloc[p + h]) / float(df.close.iloc[p]) - 1 for p in positions if p + h < len(df)]
        base_pos = baseline_positions(df, h)
        baseline_values = [float(df.close.iloc[p + h]) / float(df.close.iloc[p]) - 1 for p in base_pos]
        sig = stats(signal_values)
        base = stats(baseline_values)
        horizons[str(h)] = {
            "signal": sig,
            "baseline": base,
            "edge": {
                "median_excess": None if sig.get("median") is None or base.get("median") is None else round(sig["median"] - base["median"], 4),
                "positive_rate_advantage_pp": None if sig.get("positive_rate") is None or base.get("positive_rate") is None else round(sig["positive_rate"] - base["positive_rate"], 1),
            },
        }
        if h in PATH_HORIZONS:
            horizons[str(h)]["path"] = path_metrics(df, positions, h)
    return horizons


def regime_splits(df: pd.DataFrame, positions: list[int], horizon: int = 10) -> list[dict]:
    groups = {
        "Above 200DMA": lambda p: safe_num(df.dist_ma200.iloc[p]) is not None and df.dist_ma200.iloc[p] >= 0,
        "Below 200DMA": lambda p: safe_num(df.dist_ma200.iloc[p]) is not None and df.dist_ma200.iloc[p] < 0,
        "VIX <20": lambda p: safe_num(df.vix.iloc[p]) is not None and df.vix.iloc[p] < 20,
        "VIX 20-30": lambda p: safe_num(df.vix.iloc[p]) is not None and 20 <= df.vix.iloc[p] < 30,
        "VIX >30": lambda p: safe_num(df.vix.iloc[p]) is not None and df.vix.iloc[p] >= 30,
    }
    out = []
    for label, fn in groups.items():
        ps = [p for p in positions if p + horizon < len(df) and fn(p)]
        vals = [float(df.close.iloc[p + horizon]) / float(df.close.iloc[p]) - 1 for p in ps]
        s = stats(vals)
        if s.get("n", 0) >= 5:
            out.append({"regime": label, "horizon": horizon, **s})
    return out


def evidence_label(n: int) -> str:
    if n < 10:
        return "Very limited"
    if n < 20:
        return "Limited"
    if n < 50:
        return "Moderate"
    if n < 100:
        return "Strong"
    return "High sample depth"


def diagnostics(horizons: dict, n: int) -> list[str]:
    flags = []
    h = horizons.get("10", {}).get("signal", {})
    mean, median = h.get("average"), h.get("median")
    p25, p75 = h.get("p25"), h.get("p75")
    edge = horizons.get("10", {}).get("edge", {}).get("median_excess")
    if mean is not None and median is not None and abs(mean - median) >= 1.0:
        flags.append("Mean and median differ materially, suggesting outlier influence.")
    if p25 is not None and p75 is not None and p75 - p25 >= 6.0:
        flags.append("Outcomes have wide historical dispersion.")
    if edge is not None and abs(edge) < 0.25:
        flags.append("Median edge versus normal market behavior is weak.")
    if n < 20:
        flags.append("Sample is too small for strong conclusions.")
    return flags


def build_commentary(study: dict) -> str:
    h = study["horizons"].get("5", {})
    sig, base, edge = h.get("signal", {}), h.get("baseline", {}), h.get("edge", {})
    if sig.get("n", 0) < 10:
        return "Prior occurrences are too limited to support a strong historical conclusion. Treat this study as context only."
    med, pos, bpos, excess = sig.get("median"), sig.get("positive_rate"), base.get("positive_rate"), edge.get("median_excess")
    if med is None or pos is None or bpos is None:
        return "Historical outcomes are available, but the sample is incomplete for a clean comparison with normal market behavior."
    direction = "more favorable" if (excess or 0) > .25 and pos > bpos else "less favorable" if (excess or 0) < -.25 and pos < bpos else "not materially different"
    return f"Historically, the 5-day outcome after this setup was {direction} than a normal {study['symbol']} 5-day period. The median was {med:+.2f}% and {pos:.0f}% of prior occurrences finished higher versus {bpos:.0f}% normally. Historical precedent is context, not a forecast."


def fetch_history(symbol: str) -> pd.DataFrame:
    df = yf.download(symbol, start=START, interval="1d", auto_adjust=True, progress=False, threads=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if df.empty:
        raise RuntimeError(f"No historical data returned for {symbol}")
    return df


def build() -> dict:
    vix_df = fetch_history("^VIX")
    vix = vix_df["Close"].astype(float)
    catalog = signal_catalog()
    studies = []
    current = []
    coverage = {}
    for symbol in ("SPY", "QQQ"):
        df = prepare(fetch_history(symbol), vix)
        coverage[symbol] = {"start": str(df.index[0].date()), "end": str(df.index[-1].date()), "sessions": len(df)}
        for spec in catalog:
            if symbol not in spec.symbol_scope:
                continue
            raw_mask = spec.detector(df).fillna(False)
            mask = cooldown(raw_mask, spec.cooldown_sessions) if spec.cooldown_sessions else raw_mask
            rows, positions = outcome_rows(df, mask)
            if not positions:
                continue
            horizons = summarize_study(df, positions)
            n_complete = horizons.get("21", {}).get("signal", {}).get("n", len(positions))
            condition_ids = list(spec.conditions) if spec.conditions else [spec.signal_id]
            study = {
                "study_id": f"{symbol.lower()}:{spec.signal_id}",
                "signal_id": spec.signal_id,
                "symbol": symbol,
                "title": f"{symbol} {spec.title}",
                "category": spec.category,
                "definition": {
                    "rule": spec.rule,
                    "event_logic": "Transition/crossing event; repeated persistent observations are not counted unless the rule explicitly says so.",
                    "cooldown_sessions": spec.cooldown_sessions,
                    "condition_logic": "ALL" if len(condition_ids) > 1 else "SINGLE",
                    "conditions": condition_ids,
                    "compound_ready": True,
                },
                "historical_sample": len(positions),
                "complete_21d_sample": n_complete,
                "first_event": rows[0]["event_date"],
                "last_event": rows[-1]["event_date"],
                "evidence": evidence_label(n_complete),
                "horizons": horizons,
                "regime_splits": regime_splits(df, positions, 10),
                "recent_events": rows[-12:],
            }
            study["diagnostics"] = diagnostics(horizons, n_complete)
            study["commentary"] = build_commentary(study)
            studies.append(study)
            if bool(mask.iloc[-1]):
                current.append({
                    "study_id": study["study_id"],
                    "signal_id": spec.signal_id,
                    "symbol": symbol,
                    "title": study["title"],
                    "event_date": str(df.index[-1].date()),
                    "rule": spec.rule,
                    "priority": spec.priority,
                    "historical_sample": len(positions),
                    "evidence": study["evidence"],
                })
    current.sort(key=lambda x: (-x["priority"], x["symbol"], x["signal_id"]))
    studies.sort(key=lambda x: (x["symbol"], x["category"], x["title"]))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "price_source": "Yahoo Finance via yfinance, adjusted daily OHLC for SPY/QQQ and Cboe VIX history distributed via Yahoo Finance",
            "start_requested": START,
            "horizons": list(HORIZONS),
            "horizon_definition": "Trading sessions after the event date, not calendar days.",
            "baseline": "All eligible trading-day windows for the same symbol over the same available history.",
            "returns": "Adjusted-close forward returns from the event close.",
            "path": "Adjusted daily high/low path after the event close through the selected horizon.",
            "hit_order": "Upside/downside first-hit probabilities use the full eligible event sample. If both thresholds occur on the same daily bar, order is marked ambiguous rather than guessed.",
            "lookahead": "Signal detection uses only information available on or before the event close; future observations are used only for outcome measurement.",
            "survivorship": "V1 price studies use index ETFs and VIX, so constituent survivorship bias is not applicable. Future breadth studies must use point-in-time constituent membership or disclose the limitation.",
        },
        "coverage": coverage,
        "current_events": current,
        "studies": studies,
    }


def main():
    payload = build()
    OUT.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    print(f"Wrote {OUT} with {len(payload['studies'])} studies and {len(payload['current_events'])} current events")


if __name__ == "__main__":
    main()
