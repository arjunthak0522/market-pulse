#!/usr/bin/env python3
"""Run Market Event Intelligence with freshness-safe context merging."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.market_events import MARKET_CONTEXT, SIGNAL_DATA, apply_events

EVENT_INPUTS = ROOT / "data" / "event_inputs.json"
EVENT_MARKET_CONTEXT = ROOT / "data" / "event_market_context.json"


def _read(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text())
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def sanitized_context(signal_payload: dict, context: dict, external: dict, current_market: dict | None = None) -> dict:
    out = dict(context)
    signal_date = str(signal_payload.get("market_date") or signal_payload.get("data_status", {}).get("session_date") or "")
    context_date = str(context.get("market_date") or "")

    # Session-specific context must match the active signal session. Never relabel stale
    # sector/ETF/breadth-cycle data as current.
    if signal_date and context_date != signal_date:
        for key in ("sector_leadership", "relative_strength", "etfs", "breadth_cycle", "equity_put_call"):
            out.pop(key, None)

    # A dedicated same-session ETF collector can restore leadership/technical context,
    # but only when its own market date exactly matches the active signal session.
    current_market = current_market or {}
    fresh_context = current_market.get("context") if isinstance(current_market.get("context"), dict) else {}
    fresh_date = str(fresh_context.get("market_date") or "")
    if signal_date and fresh_date == signal_date:
        for key in ("sector_leadership", "relative_strength", "etfs"):
            if key in fresh_context:
                out[key] = fresh_context[key]
        out["market_context_source_status"] = {
            "generated_at": current_market.get("generated_at"),
            "freshness": current_market.get("freshness"),
            "confidence": current_market.get("confidence"),
            "source": current_market.get("source"),
            "error": current_market.get("error"),
        }

    ext_inputs = external.get("event_inputs") if isinstance(external.get("event_inputs"), dict) else {}
    out["event_inputs"] = ext_inputs
    out["event_source_status"] = {
        "generated_at": external.get("generated_at"),
        "errors": external.get("errors") or {},
        "fallbacks_in_use": external.get("fallbacks_in_use") or {},
        "failure_rule": external.get("failure_rule"),
    }
    return out


def run() -> dict:
    signal = _read(SIGNAL_DATA)
    context = _read(MARKET_CONTEXT)
    external = _read(EVENT_INPUTS)
    current_market = _read(EVENT_MARKET_CONTEXT)
    merged = sanitized_context(signal, context, external, current_market)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(merged, f, allow_nan=False)
        temp = Path(f.name)
    try:
        return apply_events(context_path=temp)
    finally:
        temp.unlink(missing_ok=True)


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
