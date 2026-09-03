#!/usr/bin/env python3
"""Deterministic Market Pulse regime classifier.

The regime layer is intentionally separate from the existing short-term Market State.
It uses only reliable inputs already present in data/signal_data.json and refuses to
invent unavailable Credit/Rates/Leadership readings.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "signal_data.json"
HISTORY = ROOT / "data" / "regime_history.json"
CORE_BUCKETS = ("trend", "breadth", "volatility")


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


def _label(score: float | None, positive="Positive", mixed="Mixed", negative="Negative") -> str:
    if score is None:
        return "Unavailable"
    if score >= 60:
        return positive
    if score < 40:
        return negative
    return mixed


def bucket_scores(payload: dict) -> dict:
    signals = payload.get("signals") or {}
    br = signals.get("breadth") or {}
    nymo = signals.get("nymo") or {}
    namo = signals.get("namo") or {}
    newlows = signals.get("newlows") or {}
    vol = signals.get("vol") or {}

    trend = _avg([
        _num(br.get("above_20d")),
        _num(br.get("above_50d")),
        _num(br.get("above_200d")),
    ])

    breadth = _avg([
        _num(br.get("above_5d")),
        _num(br.get("above_20d")),
        _num(nymo.get("percentile_252d")),
        _num(namo.get("percentile_252d")),
        None if _num(newlows.get("percentile_252d")) is None else 100 - _num(newlows.get("percentile_252d")),
    ])

    term_pct = _num(vol.get("term_percentile_252d"))
    vvix_pct = _num(vol.get("vvix_percentile_252d"))
    skew_pct = _num(vol.get("skew_percentile_252d"))
    term_ratio = _num(vol.get("term_ratio"))
    vol_stress = max([x for x in (term_pct, vvix_pct, skew_pct) if x is not None], default=None)
    if term_ratio is not None and term_ratio >= 1.0:
        vol_stress = max(vol_stress or 0, 90 + min(10, (term_ratio - 1.0) * 100))
    volatility = None if vol_stress is None else 100 - _clamp(vol_stress)

    return {
        "trend": {
            "score": None if trend is None else round(_clamp(trend), 1),
            "label": _label(trend),
            "detail": "S&P 500 participation above 20-, 50-, and 200-day trends.",
        },
        "breadth": {
            "score": None if breadth is None else round(_clamp(breadth), 1),
            "label": _label(breadth, "Broad", "Mixed", "Weak"),
            "detail": "Short-term participation, NYSE/Nasdaq breadth momentum, and new-low pressure.",
        },
        "volatility": {
            "score": None if volatility is None else round(_clamp(volatility), 1),
            "label": _label(volatility, "Contained", "Elevated", "Stressed"),
            "detail": "VIX term structure, VVIX, and SKEW. Higher score means calmer conditions.",
        },
    }


def _recovery_candidate(buckets: dict, previous: dict | None) -> tuple[str, str, float] | None:
    if not previous or previous.get("official") not in {"Risk-Off", "Volatility Shock"}:
        return None
    scores = previous.get("scores") or {}
    b = buckets["breadth"]["score"]
    v = buckets["volatility"]["score"]
    old_b = _num(scores.get("breadth"))
    old_v = _num(scores.get("volatility"))
    if b is None or v is None or old_b is None or old_v is None:
        return None
    breadth_gain = b - old_b
    vol_gain = v - old_v
    if breadth_gain >= 10 and vol_gain >= 8 and b >= 35:
        margin = min(breadth_gain - 10, vol_gain - 8) + 6
        return (
            "Recovery / Re-Risking",
            "Breadth is repairing and volatility is easing after a defensive regime, but the recovery still needs persistence.",
            max(6.0, margin),
        )
    return None


def candidate_regime(buckets: dict, payload: dict, previous: dict | None = None) -> tuple[str, str, float]:
    t = buckets["trend"]["score"]
    b = buckets["breadth"]["score"]
    v = buckets["volatility"]["score"]
    if sum(x is not None for x in (t, b, v)) < 2:
        return "Unavailable", "Insufficient reliable inputs to classify the market regime.", 0.0

    vol = (payload.get("signals") or {}).get("vol") or {}
    term_ratio = _num(vol.get("term_ratio"))
    vol_stress = None if v is None else 100 - v

    if vol_stress is not None and (vol_stress >= 92 or ((term_ratio or 0) >= 1.0 and vol_stress >= 80)):
        return "Volatility Shock", "Near-term volatility stress is dominating the market environment.", max(0.0, vol_stress - 80)
    recovery = _recovery_candidate(buckets, previous)
    if recovery:
        return recovery
    if t is not None and b is not None and t < 40 and b < 40:
        return "Risk-Off", "Trend and market participation are both weak, indicating broad defensive conditions.", min(40 - t, 40 - b)
    if t is not None and b is not None and t >= 60 and b >= 60 and (v is None or v >= 50):
        return "Risk-On Expansion", "Trend is positive, participation is broad, and volatility is not dominating.", min(t - 60, b - 60, (v - 50) if v is not None else 15)
    if t is not None and t >= 60 and b is not None and b < 50:
        return "Risk-On Narrowing", "The broader trend is still positive, but participation underneath the indexes is thinning.", min(t - 60, 50 - b)
    return "Transition / Mixed", "The major regime inputs are not aligned strongly enough for a clear risk-on or risk-off call.", 8.0


def _load_history(path: Path = HISTORY) -> dict:
    try:
        obj = json.loads(path.read_text())
        if isinstance(obj, dict) and isinstance(obj.get("sessions"), list):
            return obj
    except Exception:
        pass
    return {"version": 1, "sessions": []}


def _previous_session(history: dict, market_date: str) -> dict | None:
    prior = [x for x in history.get("sessions", []) if str(x.get("date", "")) < market_date]
    return prior[-1] if prior else None


def _candidate_persistence(history: dict, market_date: str, candidate: str) -> int:
    prior = [x for x in history.get("sessions", []) if str(x.get("date", "")) < market_date]
    count = 1
    for row in reversed(prior):
        if row.get("candidate") != candidate:
            break
        count += 1
    return count


def classify(payload: dict, history: dict | None = None) -> tuple[dict, dict]:
    history = history or {"version": 1, "sessions": []}
    market_date = str(payload.get("market_date") or "")
    buckets = bucket_scores(payload)
    previous = _previous_session(history, market_date)
    candidate, interpretation, margin = candidate_regime(buckets, payload, previous)
    persistence = _candidate_persistence(history, market_date, candidate)

    prev_official = previous.get("official") if previous else None
    immediate = candidate == "Volatility Shock"
    if candidate == "Unavailable":
        official = prev_official or "Unavailable"
    elif prev_official and candidate != prev_official and not immediate and persistence < 2:
        official = prev_official
        interpretation = f"{candidate} is emerging, but Market Pulse is waiting for a second completed session before changing the official regime."
    else:
        official = candidate

    if previous and official == previous.get("official"):
        start_date = previous.get("start_date") or previous.get("date")
        sessions = int(previous.get("sessions_in_regime") or 1) + (1 if market_date != previous.get("date") else 0)
    else:
        start_date = market_date
        sessions = 1

    available = sum(1 for key in CORE_BUCKETS if buckets[key]["score"] is not None)
    completeness = available / len(CORE_BUCKETS)
    aligned = 0
    if official == "Risk-On Expansion":
        aligned = sum((buckets[k]["score"] or 0) >= 60 for k in CORE_BUCKETS)
    elif official in {"Risk-Off", "Volatility Shock"}:
        aligned = sum((buckets[k]["score"] or 100) < 40 for k in CORE_BUCKETS)
    elif official == "Risk-On Narrowing":
        aligned = int((buckets["trend"]["score"] or 0) >= 60) + int((buckets["breadth"]["score"] or 100) < 50)
    elif official == "Recovery / Re-Risking":
        aligned = int((buckets["breadth"]["score"] or 0) >= 35) + int((buckets["volatility"]["score"] or 0) >= 35)
    else:
        aligned = 1

    if completeness < 2 / 3:
        confidence = "LOW"
    elif margin >= 15 and (persistence >= 2 or immediate) and aligned >= 2:
        confidence = "HIGH"
    elif margin >= 6 and completeness == 1:
        confidence = "MODERATE"
    else:
        confidence = "LOW"

    previous_name = previous.get("official") if previous else None
    transition = "No prior regime history" if not previous_name else ("Unchanged" if previous_name == official else f"{previous_name} → {official}")

    result = {
        "name": official,
        "candidate": candidate,
        "confidence": confidence,
        "interpretation": interpretation,
        "transition": transition,
        "previous_regime": previous_name,
        "start_date": start_date,
        "sessions_in_regime": sessions,
        "candidate_persistence_sessions": persistence,
        "coverage": {
            "core_available": available,
            "core_total": len(CORE_BUCKETS),
            "note": "V1 uses Trend, Breadth, and Volatility from the active Market Pulse feed. Credit, Rates, and Leadership are not fabricated when unavailable.",
        },
        "buckets": buckets,
        "stability": {
            "rule": "A non-shock regime change requires the candidate to persist for two completed sessions. Volatility Shock may trigger immediately.",
            "boundary_margin": round(float(margin), 1),
        },
    }

    session_row = {
        "date": market_date,
        "candidate": candidate,
        "official": official,
        "confidence": confidence,
        "start_date": start_date,
        "sessions_in_regime": sessions,
        "scores": {k: buckets[k]["score"] for k in CORE_BUCKETS},
    }
    sessions_list = [x for x in history.get("sessions", []) if x.get("date") != market_date]
    sessions_list.append(session_row)
    sessions_list = sorted(sessions_list, key=lambda x: str(x.get("date", "")))[-260:]
    return result, {"version": 1, "sessions": sessions_list}


def apply_regime(data_path: Path = DATA, history_path: Path = HISTORY) -> dict:
    payload = json.loads(data_path.read_text())
    history = _load_history(history_path)
    regime, updated_history = classify(payload, history)
    payload["market_regime"] = regime
    data_path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    history_path.write_text(json.dumps(updated_history, indent=2, allow_nan=False) + "\n")
    return regime


if __name__ == "__main__":
    result = apply_regime()
    print(json.dumps(result, indent=2))