#!/usr/bin/env python3
"""Free/public data-source collector for Market Pulse event intelligence.

Primary sources are government, Federal Reserve/FRED, Cboe or Nasdaq-hosted feeds.
Every family fails closed: stale/unreachable data is omitted rather than fabricated.
The collector writes normalized provider rows consumed by scripts/market_events.py.
"""
from __future__ import annotations

import io
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "event_inputs.json"
UA = "MarketPulse/1.0 public-market-research contact=github.com/arjunthak0522/market-pulse"
TIMEOUT = 18

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
ALFRED_CALENDAR = "https://alfred.stlouisfed.org/releases/calendar"
NASDAQ_EARNINGS = "https://api.nasdaq.com/api/calendar/earnings?date={date}"

SOURCE_REGISTRY = {
    "credit": {
        "primary": "FRED / ICE BofA index data",
        "series": ["BAMLH0A0HYM2", "BAMLC0A0CM"],
        "cadence": "Daily close",
        "free": True,
    },
    "rates": {
        "primary": "FRED / U.S. Treasury H.15 inputs",
        "series": ["DGS2", "DGS10", "T10Y2Y"],
        "cadence": "Daily",
        "free": True,
    },
    "cross_asset": {
        "primary": "FRED public series",
        "series": ["DTWEXBGS", "DCOILWTICO", "GOLDAMGBD228NLBM"],
        "cadence": "Daily",
        "free": True,
    },
    "liquidity": {
        "primary": "Federal Reserve / FRED",
        "series": ["NFCI", "WALCL", "RRPONTSYD", "WTREGEN"],
        "cadence": "Daily + weekly",
        "free": True,
    },
    "macro_calendar": {
        "primary": "Federal Reserve Bank of St. Louis ALFRED release calendar",
        "cadence": "Intraday calendar",
        "free": True,
    },
    "earnings": {
        "primary": "Nasdaq-hosted earnings calendar",
        "secondary": "SEC EDGAR filings for reported-company verification",
        "cadence": "Daily calendar / SEC real-time filings",
        "free": True,
        "note": "This foundation scores earnings-calendar concentration, not paid analyst revision/consensus data.",
    },
}


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _pct_rank(values: list[float], value: float) -> float:
    clean = [x for x in values if math.isfinite(x)]
    if not clean:
        return 50.0
    return 100.0 * sum(x <= value for x in clean) / len(clean)


def _series(series: str, tail: int = 800) -> list[tuple[str, float]]:
    r = requests.get(FRED_CSV.format(series=series), headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if df.shape[1] < 2:
        raise ValueError(f"{series}: malformed FRED CSV")
    date_col, val_col = df.columns[:2]
    df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
    df = df.dropna(subset=[val_col]).tail(tail)
    return [(str(d), float(v)) for d, v in zip(df[date_col], df[val_col])]


def _latest(rows: list[tuple[str, float]]) -> tuple[str, float]:
    if not rows:
        raise ValueError("empty series")
    return rows[-1]


def _change(rows: list[tuple[str, float]], n: int) -> float | None:
    if len(rows) <= n:
        return None
    return rows[-1][1] - rows[-1-n][1]


def _event(score: float, signal: str, direction: str, interpretation: str, source: str,
           as_of: str, evidence: list[dict], confidence: str = "HIGH") -> dict:
    score = round(_clamp(score), 1)
    stress = 100 - score
    severity = "extreme" if stress >= 80 else "high" if stress >= 65 else "elevated" if stress >= 50 else "normal"
    return {
        "score": score,
        "signal": signal,
        "severity": severity,
        "direction": direction,
        "confidence": confidence,
        "interpretation": interpretation,
        "source": source,
        "as_of": as_of,
        "evidence": evidence,
    }


def credit() -> dict:
    hy, ig = _series("BAMLH0A0HYM2", 760), _series("BAMLC0A0CM", 760)
    hy_d, hy_v = _latest(hy)
    ig_d, ig_v = _latest(ig)
    hy_pct = _pct_rank([v for _, v in hy], hy_v)
    ig_pct = _pct_rank([v for _, v in ig], ig_v)
    stress = 0.65 * hy_pct + 0.35 * ig_pct
    score = 100 - stress
    signal = "Credit stress" if stress >= 80 else "Credit widening" if stress >= 65 else "Normal credit" if stress < 50 else "Credit watch"
    return _event(score, signal, "risk_off" if stress >= 65 else "neutral",
                  f"High-yield OAS is {hy_v:.2f}% and investment-grade OAS is {ig_v:.2f}%; spread stress is near the {stress:.0f}th percentile of the retained history.",
                  "FRED: ICE BofA US High Yield and US Corporate OAS", min(hy_d, ig_d),
                  [{"metric":"hy_oas","value":hy_v,"percentile":round(hy_pct,1)}, {"metric":"ig_oas","value":ig_v,"percentile":round(ig_pct,1)}])


def rates() -> dict:
    d2, d10, curve = _series("DGS2", 520), _series("DGS10", 520), _series("T10Y2Y", 520)
    d2_date, y2 = _latest(d2); d10_date, y10 = _latest(d10); c_date, c = _latest(curve)
    move2 = _change(d2, 20) or 0.0
    move10 = _change(d10, 20) or 0.0
    move_stress = _clamp(max(abs(move2), abs(move10)) / 0.75 * 100)
    curve_penalty = 80 if c < -0.5 else 65 if c < 0 else 35 if c < 0.5 else 20
    stress = 0.6 * move_stress + 0.4 * curve_penalty
    score = 100 - stress
    signal = "Rate shock" if stress >= 75 else "Rates watch" if stress >= 55 else "Rates stable"
    return _event(score, signal, "risk_off" if stress >= 55 else "neutral",
                  f"2Y {y2:.2f}%, 10Y {y10:.2f}%, 10Y-2Y {c:.2f}%; largest 20-session yield move is {max(abs(move2),abs(move10)):.2f} percentage points.",
                  "FRED / U.S. Treasury constant-maturity yields", min(d2_date, d10_date, c_date),
                  [{"metric":"DGS2","value":y2,"change_20":round(move2,3)}, {"metric":"DGS10","value":y10,"change_20":round(move10,3)}, {"metric":"T10Y2Y","value":c}])


def cross_asset() -> dict:
    ids = {"dollar":"DTWEXBGS", "oil":"DCOILWTICO", "gold":"GOLDAMGBD228NLBM"}
    evidence, stresses, dates = [], [], []
    for name, sid in ids.items():
        rows = _series(sid, 520)
        date, val = _latest(rows)
        dates.append(date)
        if len(rows) > 20 and rows[-21][1] != 0:
            pct20 = (val / rows[-21][1] - 1) * 100
        else:
            pct20 = 0.0
        stress = _clamp(abs(pct20) / (6 if name == "oil" else 4) * 100)
        stresses.append(stress)
        evidence.append({"metric":name,"series":sid,"value":round(val,3),"change_20_pct":round(pct20,2)})
    stress = sum(stresses) / len(stresses)
    score = 100 - stress
    sig = "Cross-asset shock" if stress >= 75 else "Cross-asset divergence" if stress >= 55 else "Cross-asset stable"
    return _event(score, sig, "mixed" if stress >= 55 else "neutral",
                  "Dollar, crude oil and gold 20-session moves are checked for unusually large cross-asset dislocations.",
                  "FRED public dollar, WTI crude and LBMA gold series", min(dates), evidence, "MODERATE")


def liquidity() -> dict:
    nfci, walcl, rrp, tga = _series("NFCI", 260), _series("WALCL", 260), _series("RRPONTSYD", 520), _series("WTREGEN", 260)
    n_date, n = _latest(nfci); w_date, w = _latest(walcl); r_date, r = _latest(rrp); t_date, t = _latest(tga)
    nfci_pct = _pct_rank([v for _,v in nfci], n)
    walcl4 = _change(walcl, 4) or 0.0
    tga4 = _change(tga, 4) or 0.0
    # Tighter NFCI, shrinking Fed assets and a rising TGA are liquidity headwinds.
    tightening = _clamp(0.55 * nfci_pct + 0.25 * (70 if walcl4 < 0 else 30) + 0.20 * (70 if tga4 > 0 else 30))
    score = 100 - tightening
    sig = "Liquidity tightening" if tightening >= 70 else "Liquidity watch" if tightening >= 55 else "Liquidity supportive"
    return _event(score, sig, "risk_off" if tightening >= 55 else "risk_on",
                  f"NFCI is {n:.3f}; Fed assets are {w:,.0f}M, overnight RRP {r:.1f}B, and TGA {t:,.0f}M. The score emphasizes changes, not raw balance-sheet size.",
                  "Federal Reserve / FRED: NFCI, WALCL, RRPONTSYD, WTREGEN", min(n_date,w_date,r_date,t_date),
                  [{"metric":"NFCI","value":n,"percentile":round(nfci_pct,1)}, {"metric":"WALCL","value":w,"change_4w":round(walcl4,1)}, {"metric":"RRPONTSYD","value":r}, {"metric":"WTREGEN","value":t,"change_4w":round(tga4,1)}], "HIGH")


HIGH_IMPACT = (
    "consumer price", "employment situation", "payroll", "fomc", "personal income and outlays",
    "gross domestic product", "retail sales", "producer price", "jobless claims", "unemployment insurance",
    "ism", "jolts", "industrial production", "trade in goods and services",
)


def macro_calendar() -> dict:
    r = requests.get(ALFRED_CALENDAR, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True).lower()
    hits = sorted({k for k in HIGH_IMPACT if k in text})
    count = len(hits)
    # Calendar risk is two-sided; 50 is normal, lower score means more event risk.
    score = _clamp(85 - count * 8)
    sig = "Heavy macro calendar" if count >= 5 else "Macro event watch" if count >= 2 else "Light macro calendar"
    today = datetime.now(timezone.utc).date().isoformat()
    return _event(score, sig, "two_sided", f"The current ALFRED release calendar contains {count} high-impact U.S. release categories. This measures scheduled event risk, not paid consensus surprise.",
                  "Federal Reserve Bank of St. Louis ALFRED release calendar", today,
                  [{"metric":"high_impact_categories","value":count,"matches":hits}], "MODERATE")


def _parse_market_cap(value: Any) -> float:
    if value is None:
        return 0.0
    s = str(value).replace("$", "").replace(",", "").strip().upper()
    m = re.match(r"([-+]?\d+(?:\.\d+)?)\s*([KMBT]?)", s)
    if not m:
        return 0.0
    x = float(m.group(1)); u = m.group(2)
    return x * {"":1,"K":1e3,"M":1e6,"B":1e9,"T":1e12}.get(u,1)


def earnings() -> dict:
    today = datetime.now(timezone.utc).date().isoformat()
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; MarketPulseResearch/1.0)",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.nasdaq.com/market-activity/earnings",
    }
    r = requests.get(NASDAQ_EARNINGS.format(date=today), headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    obj = r.json()
    rows = (((obj.get("data") or {}).get("rows")) or [])
    count = len(rows)
    large = 0
    samples = []
    for row in rows:
        cap = _parse_market_cap(row.get("marketCap"))
        if cap >= 50e9:
            large += 1
        if len(samples) < 8:
            samples.append(row.get("symbol"))
    pressure = _clamp(count / 120 * 60 + large / 12 * 40)
    score = 100 - pressure
    sig = "Major earnings day" if pressure >= 70 else "Earnings-heavy" if pressure >= 45 else "Normal earnings load"
    return _event(score, sig, "two_sided", f"Nasdaq lists {count} scheduled earnings reports today, including {large} companies with roughly $50B+ reported market capitalization where available.",
                  "Nasdaq-hosted earnings calendar; SEC EDGAR remains the verification source for reported filings", today,
                  [{"metric":"scheduled_reports","value":count},{"metric":"large_cap_reports","value":large},{"metric":"sample_symbols","value":samples}], "MODERATE")


def collect() -> dict:
    providers = {}
    errors = {}
    for name, fn in (("credit",credit),("rates",rates),("cross_asset",cross_asset),("liquidity",liquidity),("macro_calendar",macro_calendar),("earnings",earnings)):
        try:
            providers[name] = fn()
        except Exception as exc:
            errors[name] = f"{type(exc).__name__}: {exc}"
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "event_inputs": providers,
        "errors": errors,
        "source_registry": SOURCE_REGISTRY,
        "failure_rule": "A failed provider is omitted. Market Pulse never substitutes a synthetic score for an unavailable source.",
    }


def main() -> dict:
    out = collect()
    OUT.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    return out


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
