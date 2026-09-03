#!/usr/bin/env python3
"""Partial historical sanity check for Market Regime.

The existing data/history.json archive contains daily S&P 500 breadth history but not
the complete V1 volatility inputs. This script therefore tests classification and
hysteresis behavior across the stored breadth history without pretending it is a full
historical backtest of the production regime model.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.market_regime import classify

SOURCE = ROOT / "data" / "history.json"


def payload_from_breadth(row: dict) -> dict:
    return {
        "market_date": row.get("date"),
        "signals": {
            "breadth": {
                "above_5d": row.get("above_5d"),
                "above_20d": row.get("above_20d"),
                "above_50d": row.get("above_50d"),
                "above_200d": row.get("above_200d"),
            },
            "nymo": {},
            "namo": {},
            "newlows": {},
            "vol": {},
        },
    }


def run(path: Path = SOURCE) -> dict:
    source = json.loads(path.read_text())
    rows = sorted(source.get("breadth") or [], key=lambda x: str(x.get("date", "")))
    assert rows, "history.json has no breadth history"

    history = {"version": 1, "sessions": []}
    outputs = []
    for row in rows:
        if not row.get("date"):
            continue
        result, history = classify(payload_from_breadth(row), history)
        outputs.append(result)

    assert outputs, "no historical sessions classified"
    allowed = {
        "Risk-On Expansion",
        "Risk-On Narrowing",
        "Transition / Mixed",
        "Volatility Shock",
        "Risk-Off",
        "Recovery / Re-Risking",
        "Unavailable",
    }
    assert all(x.get("name") in allowed for x in outputs), "unknown regime emitted"
    assert not any(x.get("candidate") == "Volatility Shock" for x in outputs), "volatility shock fabricated without volatility data"

    official = [x["name"] for x in outputs]
    transitions = sum(1 for a, b in zip(official, official[1:]) if a != b)
    counts = Counter(official)
    return {
        "sessions": len(outputs),
        "first_date": rows[0].get("date"),
        "last_date": rows[-1].get("date"),
        "official_transitions": transitions,
        "regime_counts": dict(sorted(counts.items())),
        "limitation": "Breadth-history-only sanity check. The archive lacks the full V1 volatility history, so this is not a predictive backtest or a complete historical regime reconstruction.",
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
