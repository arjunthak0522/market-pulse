import unittest

from scripts.market_regime import classify


def payload(date, trend=(75, 72, 70), breadth=(70, 68), nymo=70, namo=68, newlows=20, term=0.85, term_pct=30, vvix=35, skew=40):
    return {
        "market_date": date,
        "signals": {
            "breadth": {
                "above_5d": breadth[0],
                "above_20d": breadth[1],
                "above_50d": trend[1],
                "above_200d": trend[2],
            },
            "nymo": {"percentile_252d": nymo},
            "namo": {"percentile_252d": namo},
            "newlows": {"percentile_252d": newlows},
            "vol": {
                "term_ratio": term,
                "term_percentile_252d": term_pct,
                "vvix_percentile_252d": vvix,
                "skew_percentile_252d": skew,
            },
        },
    }


def prior(date, candidate, official, scores, start_date=None, sessions=1):
    return {
        "date": date,
        "candidate": candidate,
        "official": official,
        "start_date": start_date or date,
        "sessions_in_regime": sessions,
        "scores": scores,
    }


class MarketRegimeTests(unittest.TestCase):
    def test_risk_on_expansion(self):
        result, _ = classify(payload("2026-09-01"), {"version": 1, "sessions": []})
        self.assertEqual(result["name"], "Risk-On Expansion")
        self.assertEqual(result["coverage"]["core_available"], 3)

    def test_narrowing_is_distinct_from_expansion(self):
        p = payload("2026-09-01", trend=(75, 72, 70), breadth=(42, 44), nymo=42, namo=45, newlows=65)
        result, _ = classify(p, {"version": 1, "sessions": []})
        self.assertEqual(result["candidate"], "Risk-On Narrowing")

    def test_non_shock_switch_requires_two_sessions(self):
        h = {"version": 1, "sessions": [prior(
            "2026-09-01", "Risk-On Expansion", "Risk-On Expansion",
            {"trend": 72, "breadth": 68, "volatility": 60},
        )]}
        weak = payload("2026-09-02", trend=(30, 28, 25), breadth=(25, 25), nymo=15, namo=20, newlows=85)
        first, h2 = classify(weak, h)
        self.assertEqual(first["candidate"], "Risk-Off")
        self.assertEqual(first["name"], "Risk-On Expansion")
        second, _ = classify({**weak, "market_date": "2026-09-03"}, h2)
        self.assertEqual(second["name"], "Risk-Off")

    def test_one_day_boundary_flip_does_not_whipsaw(self):
        h = {"version": 1, "sessions": [prior(
            "2026-09-01", "Risk-On Expansion", "Risk-On Expansion",
            {"trend": 66, "breadth": 64, "volatility": 61},
        )]}
        mixed = payload("2026-09-02", trend=(58, 57, 58), breadth=(55, 55), nymo=52, namo=52, newlows=45)
        first, h2 = classify(mixed, h)
        self.assertEqual(first["candidate"], "Transition / Mixed")
        self.assertEqual(first["name"], "Risk-On Expansion")
        rebound = payload("2026-09-03")
        second, _ = classify(rebound, h2)
        self.assertEqual(second["name"], "Risk-On Expansion")

    def test_volatility_shock_can_trigger_immediately(self):
        h = {"version": 1, "sessions": [prior(
            "2026-09-01", "Risk-On Expansion", "Risk-On Expansion",
            {"trend": 72, "breadth": 68, "volatility": 60},
        )]}
        shocked = payload("2026-09-02", term=1.08, term_pct=95, vvix=96, skew=94)
        result, _ = classify(shocked, h)
        self.assertEqual(result["candidate"], "Volatility Shock")
        self.assertEqual(result["name"], "Volatility Shock")

    def test_recovery_requires_breadth_and_volatility_repair(self):
        h = {"version": 1, "sessions": [prior(
            "2026-09-01", "Risk-Off", "Risk-Off",
            {"trend": 28, "breadth": 20, "volatility": 18},
        )]}
        recovering = payload("2026-09-02", trend=(42, 42, 43), breadth=(45, 45), nymo=48, namo=45, newlows=58, term_pct=48, vvix=50, skew=52)
        first, h2 = classify(recovering, h)
        self.assertEqual(first["candidate"], "Recovery / Re-Risking")
        self.assertEqual(first["name"], "Risk-Off")
        second, _ = classify({**recovering, "market_date": "2026-09-03"}, h2)
        self.assertEqual(second["name"], "Recovery / Re-Risking")

    def test_recovery_not_called_on_breadth_only_bounce(self):
        h = {"version": 1, "sessions": [prior(
            "2026-09-01", "Risk-Off", "Risk-Off",
            {"trend": 28, "breadth": 20, "volatility": 18},
        )]}
        p = payload("2026-09-02", trend=(42, 42, 43), breadth=(48, 46), nymo=50, namo=48, newlows=55, term_pct=88, vvix=90, skew=89)
        result, _ = classify(p, h)
        self.assertNotEqual(result["candidate"], "Recovery / Re-Risking")

    def test_missing_data_does_not_fake_regime(self):
        p = {"market_date": "2026-09-01", "signals": {"breadth": {}, "nymo": {}, "namo": {}, "newlows": {}, "vol": {}}}
        result, _ = classify(p, {"version": 1, "sessions": []})
        self.assertEqual(result["name"], "Unavailable")
        self.assertEqual(result["confidence"], "LOW")


if __name__ == "__main__":
    unittest.main()
