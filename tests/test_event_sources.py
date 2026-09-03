import unittest

from scripts.event_sources import SOURCE_REGISTRY
from scripts.run_event_intelligence import sanitized_context


class EventSourceTests(unittest.TestCase):
    def test_all_external_families_have_free_source_registry(self):
        expected = {"credit", "rates", "cross_asset", "liquidity", "macro_calendar", "earnings"}
        self.assertEqual(set(SOURCE_REGISTRY), expected)
        for row in SOURCE_REGISTRY.values():
            self.assertTrue(row.get("free"))
            self.assertTrue(row.get("primary"))
            self.assertTrue(row.get("cadence"))

    def test_stale_session_context_is_removed(self):
        signal = {"market_date": "2026-09-03"}
        context = {
            "market_date": "2026-09-02",
            "sector_leadership": [{"name": "Technology"}],
            "relative_strength": {"qqq_vs_spy_20d": 1},
            "etfs": {"SPY": {"rsi14": 50}},
            "breadth_cycle": {"state": "old"},
            "equity_put_call": {"value": 0.7},
            "other": "keep",
        }
        out = sanitized_context(signal, context, {"event_inputs": {}})
        for key in ("sector_leadership", "relative_strength", "etfs", "breadth_cycle", "equity_put_call"):
            self.assertNotIn(key, out)
        self.assertEqual(out["other"], "keep")

    def test_matching_context_is_preserved_and_external_inputs_merge(self):
        signal = {"market_date": "2026-09-03"}
        context = {"market_date": "2026-09-03", "sector_leadership": [{"name": "Technology"}]}
        external = {"generated_at": "x", "event_inputs": {"credit": {"score": 80}}, "errors": {}}
        out = sanitized_context(signal, context, external)
        self.assertIn("sector_leadership", out)
        self.assertEqual(out["event_inputs"]["credit"]["score"], 80)


if __name__ == "__main__":
    unittest.main()
