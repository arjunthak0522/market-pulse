#!/usr/bin/env python3
"""Deterministic Market Pulse event-intelligence foundation.

This layer is broader than Market Regime. It normalizes every supported market-event
family into one stable contract, ranks what matters now, and refuses to fabricate
missing inputs. New data providers can be added family-by-family without changing
consumers of the event contract.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SIGNAL_DATA = ROOT / "data" / "signal_data.json"
MARKET_CONTEXT = ROOT / "data" / "market_context.json"
EVENT_HISTORY = ROOT / "data" / "event_history.json"

EVENT_FAMILIES = (
    "trend",
    "breadth",
    "volatility",
    "credit",
    "rates",
    "leadership",
    "cross_asset",
    "sentiment",
    "positioning_options",
    "macro_calendar",
    "liquidity",
    "earnings",
    "technical_extremes",
)


def _num(value: Any) -> float | None:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if value == value else None


def _avg(values: list[float | None]) -> float | None:
    clean = [x for x in values if x is not None]
    return sum(clean) / len(clean) if clean else None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _severity_from_score(score: float | None, inverse: bool = False) -> str:
    if score is None:
        return "unavailable"
    stress = score if inverse else 100 - score
    if stress >= 80:
        return "extreme"
    if stress >= 65:
        return "high"
    if stress >= 50:
        return "elevated"
    return "normal"


def _event(family: str, *, status: str, score: float | None, severity: str,
           signal: str, interpretation: str, source: str, as_of: str | None,
           direction: str = "neutral", confidence: str = "MODERATE",
           evidence: list[dict] | None = None) -> dict:
    return {
        "family": family,
        "status": status,
        "score": None if score is None else round(_clamp(score), 1),
        "severity": severity,
        "direction": direction,
        "confidence": confidence,
        "signal": signal,
        "interpretation": interpretation,
        "source": source,
        "as_of": as_of,
        "evidence": evidence or [],
    }


def _unavailable(family: str, source: str, note: str) -> dict:
    return _event(
        family,
        status="unavailable",
        score=None,
        severity="unavailable",
        direction="unknown",
        confidence="LOW",
        signal="Unavailable",
        interpretation=note,
        source=source,
        as_of=None,
    )


def _trend(signals: dict, context: dict, date: str) -> dict:
    br = signals.get("breadth") or {}
    score = _avg([_num(br.get("above_20d")), _num(br.get("above_50d")), _num(br.get("above_200d"))])
    if score is None:
        return _unavailable("trend", "Market Pulse breadth feed", "Trend participation is unavailable.")
    signal = "Positive" if score >= 60 else "Weak" if score < 40 else "Mixed"
    return _event("trend", status="available", score=score, severity=_severity_from_score(score),
                  direction="risk_on" if score >= 60 else "risk_off" if score < 40 else "mixed",
                  signal=signal, interpretation=f"{score:.0f}% average participation across 20-, 50-, and 200-day trends.",
                  source="Market Pulse breadth feed", as_of=date,
                  evidence=[{"metric":"trend_participation","value":round(score,1)}])


def _breadth(signals: dict, context: dict, date: str) -> dict:
    br, nymo, namo, lows = (signals.get("breadth") or {}, signals.get("nymo") or {}, signals.get("namo") or {}, signals.get("newlows") or {})
    low_pct = _num(lows.get("percentile_252d"))
    score = _avg([_num(br.get("above_5d")), _num(br.get("above_20d")), _num(nymo.get("percentile_252d")), _num(namo.get("percentile_252d")), None if low_pct is None else 100-low_pct])
    if score is None:
        return _unavailable("breadth", "Market Pulse breadth feeds", "Breadth inputs are unavailable.")
    cycle = context.get("breadth_cycle") or {}
    signal = "Broad" if score >= 60 else "Weak" if score < 40 else "Mixed"
    interpretation = cycle.get("read") or f"Breadth composite is {score:.0f}/100."
    return _event("breadth", status="available", score=score, severity=_severity_from_score(score),
                  direction="risk_on" if score >= 60 else "risk_off" if score < 40 else "mixed",
                  signal=signal, interpretation=interpretation, source="Market Pulse breadth feeds", as_of=date,
                  evidence=[{"metric":"breadth_composite","value":round(score,1)}, {"metric":"cycle_state","value":cycle.get("state")}])


def _volatility(signals: dict, context: dict, date: str) -> dict:
    vol = signals.get("vol") or {}
    term, vvix, skew, ratio = map(_num, (vol.get("term_percentile_252d"), vol.get("vvix_percentile_252d"), vol.get("skew_percentile_252d"), vol.get("term_ratio")))
    stress = max([x for x in (term, vvix, skew) if x is not None], default=None)
    if ratio is not None and ratio >= 1:
        stress = max(stress or 0, 90 + min(10, (ratio-1)*100))
    if stress is None:
        return _unavailable("volatility", "Market Pulse volatility feed", "Volatility structure is unavailable.")
    calm = 100 - _clamp(stress)
    signal = "Contained" if calm >= 60 else "Stressed" if calm < 40 else "Elevated"
    return _event("volatility", status="available", score=calm, severity=_severity_from_score(calm),
                  direction="risk_on" if calm >= 60 else "risk_off" if calm < 40 else "mixed",
                  signal=signal, interpretation="VIX term structure, VVIX and SKEW are normalized into one volatility-stress reading.",
                  source="Market Pulse volatility feed", as_of=date,
                  evidence=[{"metric":"term_ratio","value":ratio},{"metric":"stress_percentile","value":round(stress,1)}])


def _leadership(signals: dict, context: dict, date: str) -> dict:
    rows = context.get("sector_leadership") or []
    if not rows:
        return _unavailable("leadership", "Market Pulse sector leadership", "Sector leadership data is unavailable.")
    leaders = [r for r in rows if r.get("status") == "Leader"]
    laggards = [r for r in rows if r.get("status") == "Lagging"]
    spread = len(leaders) - len(laggards)
    score = _clamp(50 + spread * 8)
    qrel = _num((context.get("relative_strength") or {}).get("qqq_vs_spy_20d"))
    signal = "Broadening" if score >= 60 else "Narrow / Defensive" if score < 40 else "Mixed"
    names = ", ".join(r.get("name", r.get("ticker","")) for r in leaders[:3]) or "none"
    return _event("leadership", status="available", score=score, severity=_severity_from_score(score),
                  direction="risk_on" if score >= 60 else "risk_off" if score < 40 else "mixed",
                  signal=signal, interpretation=f"Sector leadership is {signal.lower()}; current leaders: {names}.",
                  source="Sector SPDR adjusted closes via Market Pulse", as_of=date,
                  evidence=[{"metric":"leaders","value":len(leaders)},{"metric":"laggards","value":len(laggards)},{"metric":"qqq_vs_spy_20d","value":qrel}])


def _sentiment(signals: dict, context: dict, date: str) -> dict:
    cpce = signals.get("cpce") or {}
    pctx = context.get("equity_put_call") or {}
    pct = _num(cpce.get("percentile_252d"))
    if pct is None:
        pct = _num(pctx.get("percentile_60d"))
    if pct is None:
        return _unavailable("sentiment", "Cboe put/call data", "Sentiment percentile is unavailable.")
    # High put/call percentile means fear. Score remains 0=stressed, 100=benign/risk-on.
    score = 100 - pct
    sig = "Fear extreme" if pct >= 90 else "Elevated fear" if pct >= 75 else "Complacent" if pct <= 15 else "Normal"
    return _event("sentiment", status="available", score=score, severity=_severity_from_score(score),
                  direction="contrarian_bullish" if pct >= 90 else "risk_off" if pct >= 75 else "neutral",
                  signal=sig, interpretation=f"Equity put/call sentiment is at approximately the {pct:.0f}th percentile of its available history.",
                  source="Cboe equity put/call via Market Pulse", as_of=date,
                  evidence=[{"metric":"put_call_percentile","value":round(pct,1)},{"metric":"put_call","value":_num(pctx.get("value"))}])


def _technical_extremes(signals: dict, context: dict, date: str) -> dict:
    etfs = context.get("etfs") or {}
    vals = []
    evidence = []
    for ticker in ("SPY","QQQ"):
        row = etfs.get(ticker) or {}
        rsi, wr, bb = _num(row.get("rsi14")), _num(row.get("williams_r14")), _num(row.get("bollinger_pct_b"))
        if rsi is not None:
            vals.append(abs(rsi-50)*2)
        if wr is not None and wr <= -80:
            vals.append(min(100, (-wr-80)*5+60))
        if bb is not None and (bb <= .1 or bb >= .9):
            vals.append(min(100, 60 + abs(bb-.5)*80))
        evidence.append({"metric":ticker,"rsi14":rsi,"williams_r14":wr,"bollinger_pct_b":bb})
    if not vals:
        return _unavailable("technical_extremes", "SPY/QQQ technical context", "Technical-extreme inputs are unavailable.")
    extreme = max(vals)
    score = 100-extreme
    sig = "Extreme" if extreme >= 80 else "Stretched" if extreme >= 60 else "Normal"
    return _event("technical_extremes", status="available", score=score, severity=_severity_from_score(score),
                  direction="two_sided", signal=sig,
                  interpretation="SPY/QQQ RSI, Williams %R and Bollinger position are checked for short-term statistical stretch.",
                  source="Market Pulse SPY/QQQ technical context", as_of=date, evidence=evidence)


def _positioning_options(signals: dict, context: dict, date: str) -> dict:
    cpce = signals.get("cpce") or {}
    vol = signals.get("vol") or {}
    pieces = [
        _num(cpce.get("percentile_252d")),
        _num(vol.get("skew_percentile_252d")),
        _num(vol.get("vvix_percentile_252d")),
    ]
    stress = _avg(pieces)
    if stress is None:
        return _unavailable("positioning_options", "Put/call, SKEW and VVIX", "Options-positioning inputs are unavailable.")
    score = 100-stress
    sig = "Defensive / Hedged" if stress >= 70 else "Neutral" if stress >= 30 else "Complacent"
    return _event("positioning_options", status="available", score=score, severity=_severity_from_score(score),
                  direction="risk_off" if stress >= 70 else "neutral", signal=sig,
                  interpretation="Put/call, SKEW and VVIX are combined as a positioning/hedging stress proxy, not as dealer GEX.",
                  source="Market Pulse options proxies", as_of=date,
                  evidence=[{"metric":"positioning_stress","value":round(stress,1)}])


def _provider_payload(context: dict, family: str) -> dict | None:
    providers = context.get("event_inputs") or {}
    row = providers.get(family)
    return row if isinstance(row, dict) else None


def _external_family(family: str, context: dict, date: str, description: str) -> dict:
    row = _provider_payload(context, family)
    if not row:
        return _unavailable(family, "event_inputs adapter", description)
    score = _num(row.get("score"))
    if score is None:
        return _unavailable(family, row.get("source") or "event_inputs adapter", f"{family} provider supplied no normalized score.")
    return _event(
        family,
        status="available",
        score=score,
        severity=row.get("severity") or _severity_from_score(score),
        direction=row.get("direction") or "neutral",
        confidence=row.get("confidence") or "MODERATE",
        signal=row.get("signal") or "Available",
        interpretation=row.get("interpretation") or description,
        source=row.get("source") or "event_inputs adapter",
        as_of=row.get("as_of") or date,
        evidence=row.get("evidence") if isinstance(row.get("evidence"), list) else [],
    )


ADAPTERS: dict[str, Callable[[dict, dict, str], dict]] = {
    "trend": _trend,
    "breadth": _breadth,
    "volatility": _volatility,
    "leadership": _leadership,
    "sentiment": _sentiment,
    "positioning_options": _positioning_options,
    "technical_extremes": _technical_extremes,
    "credit": lambda s,c,d: _external_family("credit", c, d, "Credit spreads/default-risk data is not yet connected."),
    "rates": lambda s,c,d: _external_family("rates", c, d, "Treasury curve/rate-shock data is not yet connected."),
    "cross_asset": lambda s,c,d: _external_family("cross_asset", c, d, "Dollar, commodities, bonds and global-risk cross-asset inputs are not yet connected."),
    "macro_calendar": lambda s,c,d: _external_family("macro_calendar", c, d, "Scheduled macro-event surprise data is not yet connected."),
    "liquidity": lambda s,c,d: _external_family("liquidity", c, d, "Financial-conditions/liquidity inputs are not yet connected."),
    "earnings": lambda s,c,d: _external_family("earnings", c, d, "Earnings breadth/revision inputs are not yet connected."),
}


def _importance(row: dict) -> float:
    if row.get("status") != "available" or row.get("score") is None:
        return 0.0
    score = float(row["score"])
    stress = abs(score - 50) * 2
    confidence = {"HIGH":1.0,"MODERATE":0.85,"LOW":0.65}.get(row.get("confidence"),0.75)
    sev = {"extreme":1.15,"high":1.05,"elevated":1.0,"normal":0.8}.get(row.get("severity"),0.8)
    return round(_clamp(stress * confidence * sev), 1)


def build_event_intelligence(signal_payload: dict, market_context: dict | None = None) -> dict:
    context = market_context or {}
    signals = signal_payload.get("signals") or {}
    date = str(signal_payload.get("market_date") or signal_payload.get("data_status",{}).get("session_date") or context.get("market_date") or "")
    families = {name: ADAPTERS[name](signals, context, date) for name in EVENT_FAMILIES}
    for row in families.values():
        row["importance"] = _importance(row)

    available = [r for r in families.values() if r.get("status") == "available"]
    ranked = sorted(available, key=lambda r: (-r["importance"], r["family"]))
    top = [
        {k:r.get(k) for k in ("family","importance","severity","direction","signal","interpretation","confidence","as_of")}
        for r in ranked[:5] if r.get("importance",0) >= 20
    ]
    unavailable = [name for name,row in families.items() if row.get("status") != "available"]
    return {
        "version": 1,
        "market_date": date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "coverage": {
            "available": len(available),
            "total": len(EVENT_FAMILIES),
            "unavailable_families": unavailable,
            "rule": "Unavailable families never receive synthetic values and never affect ranking or regime confidence.",
        },
        "families": families,
        "top_events": top,
        "ranking_rule": "Importance reflects distance from neutral, confidence and severity. It ranks current conditions; it is not a forecast by itself.",
    }


def _read(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text())
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def apply_events(signal_path: Path = SIGNAL_DATA, context_path: Path = MARKET_CONTEXT, history_path: Path = EVENT_HISTORY) -> dict:
    signal_payload = _read(signal_path)
    context = _read(context_path)
    result = build_event_intelligence(signal_payload, context)
    signal_payload["market_events"] = result
    signal_path.write_text(json.dumps(signal_payload, indent=2, allow_nan=False)+"\n")

    hist = _read(history_path)
    sessions = hist.get("sessions") if isinstance(hist.get("sessions"), list) else []
    date = result.get("market_date")
    row = {
        "date": date,
        "coverage": result["coverage"],
        "top_events": result["top_events"],
        "scores": {k:v.get("score") for k,v in result["families"].items()},
    }
    sessions = [x for x in sessions if x.get("date") != date]
    sessions.append(row)
    sessions = sorted(sessions, key=lambda x: str(x.get("date", "")))[-520:]
    history_path.write_text(json.dumps({"version":1,"sessions":sessions}, indent=2, allow_nan=False)+"\n")
    return result


if __name__ == "__main__":
    print(json.dumps(apply_events(), indent=2))
