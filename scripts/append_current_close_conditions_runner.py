#!/usr/bin/env python3
from __future__ import annotations

import append_current_close_conditions as mod

_original = mod.study

def _study_compat(symbol, signal_id, title, rule, df, mask, target_date, priority, diagnostics=None):
    # The first implementation passed the two trailing args in reverse order
    # for the price-condition catalog. Normalize both call shapes here so the
    # end-of-day workflow remains deterministic while the module API stays
    # backward compatible.
    if isinstance(target_date, (int, float)) and isinstance(priority, str):
        target_date, priority = priority, target_date
    return _original(symbol, signal_id, title, rule, df, mask, target_date, priority, diagnostics)

mod.study = _study_compat
mod.main()
