#!/usr/bin/env python3
"""Market event-source runner with current cross-asset gold source.

Keeps the base collector stable while replacing FRED's retired London gold series with
NASDAQQGLDI, a current daily Nasdaq gold index distributed by FRED.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from scripts import event_sources as base


base.SOURCE_REGISTRY["cross_asset"] = {
    "primary": "FRED public daily series",
    "series": ["DTWEXBGS", "DCOILWTICO", "NASDAQQGLDI"],
    "cadence": "Daily",
    "free": True,
    "note": "Gold uses the current Nasdaq Gold FLOWS103 Price Index distributed by FRED after the prior London gold series was retired.",
}


def cross_asset() -> dict:
    ids = {"dollar": "DTWEXBGS", "oil": "DCOILWTICO", "gold": "NASDAQQGLDI"}
    evidence, stresses, dates = [], [], []
    for name, sid in ids.items():
        rows = base._series(sid, 520)
        date, val = base._latest(rows)
        dates.append(date)
        pct20 = (val / rows[-21][1] - 1) * 100 if len(rows) > 20 and rows[-21][1] != 0 else 0.0
        threshold = 8 if name == "oil" else 4
        stresses.append(base._clamp(abs(pct20) / threshold * 100))
        evidence.append({"metric": name, "series": sid, "value": round(val, 3), "change_20_pct": round(pct20, 2)})
    stress = sum(stresses) / len(stresses)
    score = 100 - stress
    signal = "Cross-asset shock" if stress >= 75 else "Cross-asset divergence" if stress >= 55 else "Cross-asset stable"
    return base._event(
        score,
        signal,
        "mixed" if stress >= 55 else "neutral",
        "Dollar, crude oil and a daily Nasdaq gold index are checked for unusually large 20-session cross-asset moves.",
        "FRED: broad dollar index, WTI crude, and Nasdaq Gold FLOWS103 Price Index",
        min(dates),
        evidence,
        "MODERATE",
    )


def collect() -> dict:
    providers, errors = {}, {}
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
            providers[name] = fn()
        except Exception as exc:
            errors[name] = f"{type(exc).__name__}: {exc}"
    return {
        "version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "event_inputs": providers,
        "errors": errors,
        "source_registry": base.SOURCE_REGISTRY,
        "failure_rule": "A failed provider is omitted. Market Pulse never substitutes a synthetic score for an unavailable source.",
    }


def main() -> dict:
    out = collect()
    base.OUT.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    return out


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
