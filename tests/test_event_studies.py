import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "update_event_studies.py"
spec = importlib.util.spec_from_file_location("event_studies", MODULE)
es = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = es
spec.loader.exec_module(es)


class EventStudyTests(unittest.TestCase):
    def test_cross_after_reset_triggers_once_on_transition(self):
        idx = pd.bdate_range("2024-01-02", periods=25)
        s = pd.Series([60.0] * 20 + [69.0, 71.0, 72.0, 68.0, 71.0], index=idx)
        mask = es.first_cross_after_reset(s, 70, 20, "above")
        hits = list(idx[mask])
        self.assertEqual(hits, [idx[21]])

    def test_cooldown_suppresses_overlapping_events(self):
        idx = pd.bdate_range("2024-01-02", periods=8)
        raw = pd.Series([False, True, True, False, True, False, True, False], index=idx)
        mask = es.cooldown(raw, 2)
        self.assertEqual(list(np.flatnonzero(mask.to_numpy())), [1, 4])

    def test_forward_returns_use_trading_session_offsets(self):
        idx = pd.bdate_range("2024-01-04", periods=70)
        close = pd.Series(np.arange(100.0, 170.0), index=idx)
        df = pd.DataFrame({"open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1}, index=idx)
        mask = pd.Series(False, index=idx)
        mask.iloc[0] = True
        rows, positions = es.outcome_rows(df, mask)
        self.assertEqual(rows[0]["event_date"], "2024-01-04")
        self.assertAlmostEqual(rows[0]["return_5d"], 5.0, places=6)
        self.assertEqual(positions, [0])

    def test_path_metrics_measure_excursion_and_hit_order(self):
        idx = pd.bdate_range("2024-01-02", periods=12)
        close = pd.Series([100, 99, 98, 101, 103, 104, 104, 104, 104, 104, 104, 104], index=idx, dtype=float)
        high = pd.Series([100, 100, 99, 102, 104, 105, 105, 105, 105, 105, 105, 105], index=idx, dtype=float)
        low = pd.Series([100, 98, 97, 99, 101, 102, 102, 102, 102, 102, 102, 102], index=idx, dtype=float)
        df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": 1}, index=idx)
        p = es.path_metrics(df, [0], 5)
        self.assertAlmostEqual(p["median_max_drawdown"], -3.0, places=6)
        self.assertAlmostEqual(p["median_max_rally"], 5.0, places=6)
        self.assertEqual(p["thresholds"]["2pct"]["reached_up"], 100.0)
        self.assertEqual(p["thresholds"]["2pct"]["reached_down"], 100.0)
        self.assertEqual(p["thresholds"]["2pct"]["downside_hit_first"], 100.0)
        self.assertEqual(p["thresholds"]["2pct"]["median_days_to_up"], 3.0)

    def test_downside_first_probability_uses_full_event_sample(self):
        idx = pd.bdate_range("2024-01-02", periods=16)
        close = pd.Series([100, 98, 98, 99, 99, 99, 100, 101, 101, 101, 101, 101, 101, 101, 101, 101], index=idx, dtype=float)
        high = close.copy()
        low = close.copy()
        low.iloc[1] = 97.0
        df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": 1}, index=idx)
        p = es.path_metrics(df, [0, 6], 5)
        t = p["thresholds"]["2pct"]
        self.assertEqual(t["reached_down"], 50.0)
        self.assertEqual(t["downside_hit_first"], 50.0)
        self.assertEqual(t["reached_up"], 0.0)

    def test_same_bar_two_sided_hit_is_ambiguous_not_guessed(self):
        idx = pd.bdate_range("2024-01-02", periods=8)
        close = pd.Series([100] * 8, index=idx, dtype=float)
        high = close.copy(); low = close.copy()
        high.iloc[1] = 103.0; low.iloc[1] = 97.0
        df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": 1}, index=idx)
        p = es.path_metrics(df, [0], 5)["thresholds"]["2pct"]
        self.assertEqual(p["same_day_order_ambiguous"], 100.0)
        self.assertEqual(p["downside_hit_first"], 0.0)
        self.assertEqual(p["upside_hit_first"], 0.0)

    def test_compound_transition_only_fires_when_all_conditions_first_align(self):
        idx = pd.bdate_range("2024-01-02", periods=6)
        df = pd.DataFrame({"a": [False, True, True, True, False, True], "b": [True, False, True, True, True, True]}, index=idx)
        detector = es.compound_transition(lambda d: d.a, lambda d: d.b)
        hits = list(idx[detector(df)])
        self.assertEqual(hits, [idx[2], idx[5]])

    def test_future_data_does_not_change_prior_signal_dates(self):
        idx = pd.bdate_range("2024-01-02", periods=30)
        base = pd.Series([50.0] * 20 + [69.0, 71.0] + [65.0] * 8, index=idx)
        mask1 = es.first_cross_after_reset(base, 70, 20, "above")
        changed = base.copy()
        changed.iloc[25:] = [90, 10, 90, 10, 90]
        mask2 = es.first_cross_after_reset(changed, 70, 20, "above")
        self.assertTrue(mask1.iloc[21])
        self.assertEqual(mask1.iloc[:22].tolist(), mask2.iloc[:22].tolist())

    def test_evidence_labels(self):
        self.assertEqual(es.evidence_label(9), "Very limited")
        self.assertEqual(es.evidence_label(10), "Limited")
        self.assertEqual(es.evidence_label(20), "Moderate")
        self.assertEqual(es.evidence_label(50), "Strong")
        self.assertEqual(es.evidence_label(100), "High sample depth")


if __name__ == "__main__":
    unittest.main()
