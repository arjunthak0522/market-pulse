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


def test_risk_on_expansion():
    result, _ = classify(payload("2026-09-01"), {"version": 1, "sessions": []})
    assert result["name"] == "Risk-On Expansion"
    assert result["coverage"]["core_available"] == 3


def test_non_shock_switch_requires_two_sessions():
    h = {"version": 1, "sessions": [{
        "date": "2026-09-01",
        "candidate": "Risk-On Expansion",
        "official": "Risk-On Expansion",
        "start_date": "2026-09-01",
        "sessions_in_regime": 1,
    }]}
    weak = payload("2026-09-02", trend=(30, 28, 25), breadth=(25, 25), nymo=15, namo=20, newlows=85)
    first, h2 = classify(weak, h)
    assert first["candidate"] == "Risk-Off"
    assert first["name"] == "Risk-On Expansion"
    second, _ = classify({**weak, "market_date": "2026-09-03"}, h2)
    assert second["name"] == "Risk-Off"


def test_volatility_shock_can_trigger_immediately():
    h = {"version": 1, "sessions": [{
        "date": "2026-09-01",
        "candidate": "Risk-On Expansion",
        "official": "Risk-On Expansion",
        "start_date": "2026-09-01",
        "sessions_in_regime": 1,
    }]}
    shocked = payload("2026-09-02", term=1.08, term_pct=95, vvix=96, skew=94)
    result, _ = classify(shocked, h)
    assert result["candidate"] == "Volatility Shock"
    assert result["name"] == "Volatility Shock"


def test_missing_data_does_not_fake_regime():
    p = {"market_date": "2026-09-01", "signals": {"breadth": {}, "nymo": {}, "namo": {}, "newlows": {}, "vol": {}}}
    result, _ = classify(p, {"version": 1, "sessions": []})
    assert result["name"] == "Unavailable"
    assert result["confidence"] == "LOW"
