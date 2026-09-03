#!/usr/bin/env python3
"""Market event-source runner with resilient free/public providers.

Uses current FRED/Nasdaq/ALFRED sources and preserves a recent last-known-good reading
when a provider has a temporary outage. Stale readings are labeled, confidence is
reduced, and every family has a hard TTL after which it becomes unavailable.
"""
from __future__ import annotations

import json
import sys
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import event_sources as base


base.SOURCE_REGISTRY["cross_asset"] = {
    "primary": "FRED public daily series",
    "series": ["DTWEXBGS", "DCOILWTICO", "NASDAQQGLDI"],
    "cadence": "Daily",
    "free": True,
    "note": "Gold uses the current Nasdaq Gold FLOWS103 Price Index distributed by FRED after the prior London gold series was retired.",
}

TTL_DAYS = {
    "credit": 4,
    "rates": 4,
    "cross_asset": 4,
    "liquidity": 10,
    "macro_calendar": 1,
    "earnings": 1,
}


def _read_previous() -> dict:
    try:
        obj = json.loads(base.OUT.read_text())
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _age_days(as_of: str | None) -> int | None:
    if not as_of:
        return None
    try:
        return max(0, (date.today() - date.fromisoformat(str(as_of)[:10])).days)
    except Exception:
        return None


def _stale_fallback(name: str, previous: dict, error: str) -> dict | None:
    prior = ((previous.get("event_inputs") or {}).get(name)) if isinstance(previous, dict) else None
    if not isinstance(prior, dict) or prior.get("score") is None:
        return None
    age = _age_days(prior.get("as_of"))
    ttl = TTL_DAYS[name]
    if age is None or age > ttl:
        return None
    row = deepcopy(prior)
    row["freshness"] = "stale_fallback"
    row["stale_age_days"] = age
    row["stale_ttl_days"] = ttl
    row["confidence"] = "LOW"
    row["refresh_error"] = error
    row["interpretation"] = (
        f"{row.get('interpretation','').rstrip()} Latest provider refresh failed, so Market Pulse is retaining the last valid reading "
        f"({age} day{'s' if age != 1 else ''} old) with LOW confidence."
    ).strip()
    return row


def cross_asset() -> dict:
    ids = {"dollar": "DTWEXBGS", "oil": "DCOILWTICO", "gold": "NASDAQQGLDI"}
    evidence, stresses, dates = [], [], []
    for name, sid in ids.items():
        rows = base._series(sid, 520)
        series_date, val = base._latest(rows)
        dates.append(series_date)
        pct20 = (val / rows[-21][1] - 1) * 100 if len(rows) > 20 and rows[-21][1] != 0 else 0.0
        threshold = 8 if name == "oil" else 4
        stresses.append(base._clamp(abs(pct20) / threshold * 100))
        evidence.append({"metric": name, "series": sid, "value": round(val, 3), "change_20_pct": round(pct20, 2)})
    stress = sum(stresses) / len(stresses)
    score = 100 - stress
    signal = "Cross-asset shock" if stress >= 75 else "Cross-asset divergence" if stress >= 55 else "Cross-asset stable"
    row = base._event(
        score,
        signal,
        "mixed" if stress >= 55 else "neutral",
        "Dollar, crude oil and a daily Nasdaq gold index are checked for unusually large 20-session cross-asset moves.",
        "FRED: broad dollar index, WTI crude, and Nasdaq Gold FLOWS103 Price Index",
        min(dates),
        evidence,
        "MODERATE",
    )
    row["freshness"] = "current_provider"
    return row


def collect() -> dict:
    providers, errors, fallbacks = {}, {}, {}
    previous = _read_previous()
    functions = (
        ("credit", base.credit),
        ("rates", base.rates),
        ("cross_asset", cross_asset),
        ("liquidity", base.liquidity),
        ("macro_calendar", base.macro_calendar),
        ("earnings", base.earnings),
    )
    for name, fn in functions:
        try:
            row = fn()
            row.setdefault("freshness", "current_provider")
            row["last_success_at"] = datetime.now(timezone.utc).isoformat()
            providers[name] = row
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            errors[name] = error
            fallback = _stale_fallback(name, previous, error)
            if fallback:
                providers[name] = fallback
                fallbacks[name] = {
                    "as_of": fallback.get("as_of"),
                    "age_days": fallback.get("stale_age_days"),
                    "ttl_days": fallback.get("stale_ttl_days"),
                }

    return {
        "version": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "event_inputs": providers,
        "errors": errors,
        "fallbacks_in_use": fallbacks,
        "source_registry": base.SOURCE_REGISTRY,
        "ttl_days": TTL_DAYS,
        "failure_rule": "Use current public data when available. On a temporary provider failure, retain a recent last-known-good value with LOW confidence only until that family's hard TTL; after TTL expiry it is omitted and becomes unavailable. Synthetic values are never created.",
    }


def main() -> dict:
    out = collect()
    base.OUT.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    return out


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
