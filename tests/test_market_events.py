import unittest

from scripts.market_events import EVENT_FAMILIES, build_event_intelligence


class MarketEventsTests(unittest.TestCase):
    def base_signal(self):
        return {
            "market_date": "2026-09-02",
            "signals": {
                "breadth": {"above_5d": 28, "above_20d": 42, "above_50d": 48, "above_200d": 63},
                "nymo": {"percentile_252d": 20},
                "namo": {"percentile_252d": 24},
                "newlows": {"percentile_252d": 82},
                "vol": {"term_ratio": 0.98, "term_percentile_252d": 78, "vvix_percentile_252d": 84, "skew_percentile_252d": 75},
                "cpce": {"percentile_252d": 91},
            },
        }

    def base_context(self):
        return {
            "market_date": "2026-09-02",
            "equity_put_call": {"value": 0.71, "percentile_60d": 92},
            "relative_strength": {"qqq_vs_spy_20d": -1.2},
            "sector_leadership": [
                {"name": "Energy", "status": "Leader"},
                {"name": "Technology", "status": "Leader"},
                {"name": "Industrials", "status": "Lagging"},
                {"name": "Discretionary", "status": "Lagging"},
            ],
            "breadth_cycle": {"state": "Approaching washout", "read": "Breadth is deteriorating toward an extreme."},
            "etfs": {
                "SPY": {"rsi14": 45, "williams_r14": -88, "bollinger_pct_b": 0.08},
                "QQQ": {"rsi14": 42, "williams_r14": -85, "bollinger_pct_b": 0.12},
            },
        }

    def test_all_event_families_are_present(self):
        out = build_event_intelligence(self.base_signal(), self.base_context())
        self.assertEqual(set(out["families"]), set(EVENT_FAMILIES))
        self.assertEqual(out["coverage"]["total"], len(EVENT_FAMILIES))

    def test_missing_external_families_are_explicitly_unavailable(self):
        out = build_event_intelligence(self.base_signal(), self.base_context())
        for name in ("credit", "rates", "cross_asset", "macro_calendar", "liquidity", "earnings"):
            self.assertEqual(out["families"][name]["status"], "unavailable")
            self.assertIsNone(out["families"][name]["score"])
            self.assertEqual(out["families"][name]["importance"], 0.0)

    def test_existing_market_pulse_inputs_populate_real_families(self):
        out = build_event_intelligence(self.base_signal(), self.base_context())
        for name in ("trend", "breadth", "volatility", "leadership", "sentiment", "positioning_options", "technical_extremes"):
            self.assertEqual(out["families"][name]["status"], "available")
            self.assertIsNotNone(out["families"][name]["score"])

    def test_external_adapter_can_be_added_without_contract_change(self):
        context = self.base_context()
        context["event_inputs"] = {
            "credit": {
                "score": 18,
                "signal": "Credit stress",
                "severity": "extreme",
                "direction": "risk_off",
                "confidence": "HIGH",
                "source": "Test credit adapter",
                "as_of": "2026-09-02",
            }
        }
        out = build_event_intelligence(self.base_signal(), context)
        self.assertEqual(out["families"]["credit"]["status"], "available")
        self.assertEqual(out["families"]["credit"]["score"], 18.0)
        self.assertEqual(out["families"]["credit"]["source"], "Test credit adapter")

    def test_top_events_only_rank_available_data(self):
        out = build_event_intelligence(self.base_signal(), self.base_context())
        ranked = {x["family"] for x in out["top_events"]}
        self.assertTrue(ranked)
        self.assertFalse(ranked.intersection({"credit", "rates", "macro_calendar", "liquidity", "earnings"}))


if __name__ == "__main__":
    unittest.main()
