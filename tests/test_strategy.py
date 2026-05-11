from datetime import datetime, timezone

from app.models import Candle, SignalAction, StrategyConfig
from app.strategy import TrendFollowingStrategy


def candles(values):
    return [Candle(ts=datetime.now(timezone.utc), open=v, high=v, low=v, close=v) for v in values]


def test_strategy_opens_long_in_uptrend_with_tp_sl():
    config = StrategyConfig(short_window=3, long_window=5, take_profit_pct=2, stop_loss_pct=1)
    signal = TrendFollowingStrategy(config).generate_signal(candles([1, 2, 3, 4, 5]))
    assert signal.action == SignalAction.OPEN_LONG
    assert signal.take_profit == 5.1
    assert signal.stop_loss == 4.95


def test_strategy_opens_short_in_downtrend_with_tp_sl():
    config = StrategyConfig(short_window=3, long_window=5, take_profit_pct=2, stop_loss_pct=1)
    signal = TrendFollowingStrategy(config).generate_signal(candles([5, 4, 3, 2, 1]))
    assert signal.action == SignalAction.OPEN_SHORT
    assert signal.take_profit == 0.98
    assert signal.stop_loss == 1.01


def test_strategy_holds_until_enough_candles():
    config = StrategyConfig(short_window=3, long_window=5)
    signal = TrendFollowingStrategy(config).generate_signal(candles([1, 2, 3]))
    assert signal.action == SignalAction.HOLD

