from signal_common.schemas import Horizon, PositionIntent, SignalAction, SignalRecord


def test_signal_record():
    r = SignalRecord(
        ticker="AAPL",
        action=SignalAction.BUY,
        horizon=Horizon.d1,
        conviction=0.7,
        master_conviction=0.7,
        technical_score=0.5,
        sentiment_score=0.4,
        regime_adjustment=0.9,
        position_intent=PositionIntent.LONG,
    )
    assert r.ticker == "AAPL"
