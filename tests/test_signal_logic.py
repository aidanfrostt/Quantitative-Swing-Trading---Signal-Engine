from signal_common.config import Settings
from signal_common.schemas import MoveAttribution
from signal_common.signal_logic import (
    apply_regime,
    blend_scores,
    build_move_attribution_narrative,
    build_thesis,
    classify_action_intent,
    fundamental_score_from_metrics,
)


def test_blend_without_fundamentals():
    s = Settings()
    v = blend_scores(0.5, 0.5, None, s)
    assert -1.0 <= v <= 1.0


def test_blend_without_fundamentals_redistributes_weights():
    s = Settings()
    # wt=0.45, ws=0.35 -> only tech+sentiment, same sign -> 1.0
    v = blend_scores(1.0, 1.0, None, s)
    assert abs(v - 1.0) < 1e-9


def test_apply_regime_scales_positive_only():
    assert abs(apply_regime(0.8, 0.5) - 0.4) < 1e-9


def test_apply_regime_leaves_negative_unscaled():
    assert abs(apply_regime(-0.5, 0.5) - (-0.5)) < 1e-9


def test_classify_long():
    s = Settings()
    a, i = classify_action_intent(0.8, s)
    assert a.value == "BUY"
    assert i.value == "long"


def test_classify_at_buy_threshold():
    s = Settings()
    a, i = classify_action_intent(s.signal_buy_threshold, s)
    assert a.value == "BUY"


def test_classify_short():
    s = Settings()
    a, i = classify_action_intent(-0.7, s)
    assert i.value == "short"


def test_classify_exit_band():
    s = Settings()
    a, i = classify_action_intent(s.signal_exit_threshold, s)
    assert a.value == "SELL"
    assert i.value == "reduce_long"


def test_fundamental_score():
    fs = fundamental_score_from_metrics(12.0, 0.18, 0.4, 0.05)
    assert -1.0 <= fs <= 1.0


def test_build_move_attribution_narrative_contains_spy():
    m = MoveAttribution(spy_return_5d=0.02, narrative="")
    text = build_move_attribution_narrative(m)
    assert "SPY" in text
    assert "2.0" in text or "2" in text


def test_build_thesis_appends_attribution():
    m = MoveAttribution(spy_return_5d=0.01, narrative="")
    t = build_thesis("ZZZ", 0.1, 0.1, None, 50.0, 0.1, "", move_attribution=m)
    assert "ZZZ" in t
    assert "SPY" in t


def test_market_calendar():
    from datetime import date

    from signal_common.market_calendar import is_nyse_trading_day

    assert is_nyse_trading_day(date(2025, 1, 2)) is True
    assert is_nyse_trading_day(date(2025, 1, 1)) is False
