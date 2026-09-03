#!/usr/bin/env python3
"""Run Market Event Intelligence with freshness-safe context merging."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from scripts.market_events import MARKET_CONTEXT, SIGNAL_DATA, apply_events

ROOT = Path(__file__).resolve().parents[1]
EVENT_INPUTS = ROOT / "data" / "event_inputs.json"


def _read(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text())
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def sanitized_context(signal_payload: dict, context: dict, external: dict) -> dict:
    out = dict(context)
    signal_date = str(signal_payload.get("market_date") or signal_payload.get("data_status", {}).get("session_date") or "")
    context_date = str(context.get("market_date") or "")

    # Session-specific context must match the active signal session. Never relabel stale
    # sector/ETF/breadth-cycle data as current.
    if signal_date and context_date != signal_date:
        for key in ("sector_leadership", "relative_strength", "etfs", "breadth_cycle", "equity_put_call"):
            out.pop(key, None)

    ext_inputs = external.get("event_inputs") if isinstance(external.get("event_inputs"), dict) else {}
    out["event_inputs"] = ext_inputs
    out["event_source_status"] = {
        "generated_at": external.get("generated_at"),
        "errors": external.get("errors") or {},
        "failure_rule": external.get("failure_rule"),
    }
    return out


def run() -> dict:
    signal = _read(SIGNAL_DATA)
    context = _read(MARKET_CONTEXT)
    external = _read(EVENT_INPUTS)
    merged = sanitized_context(signal, context, external)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(merged, f, allow_nan=False)
        temp = Path(f.name)
    try:
        return apply_events(context_path=temp)
    finally:
        temp.unlink(missing_ok=True)


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
