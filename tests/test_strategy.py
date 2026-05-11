from datetime import datetime, timezone

from app.models import Candle, SignalAction, StrategyConfig
from app.presets import xau_short_scalp_preset
from app.strategy import BreakoutStrategy, MeanReversionStrategy, TrendFollowingStrategy, XauShortScalpStrategy


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


def test_breakout_strategy_opens_long_on_new_high():
    config = StrategyConfig(breakout_window=5, take_profit_pct=2, stop_loss_pct=1)
    signal = BreakoutStrategy(config).generate_signal(candles([10, 11, 12, 13, 14, 15]))
    assert signal.action == SignalAction.OPEN_LONG
    assert signal.take_profit == 15.3
    assert signal.stop_loss == 14.85


def test_mean_reversion_opens_short_when_far_above_mean():
    config = StrategyConfig(mean_window=5, mean_reversion_threshold_pct=5, take_profit_pct=1, stop_loss_pct=1)
    signal = MeanReversionStrategy(config).generate_signal(candles([100, 100, 100, 100, 130]))
    assert signal.action == SignalAction.OPEN_SHORT


def test_xau_short_scalp_preset_opens_long_on_filtered_breakout():
    config = xau_short_scalp_preset()
    values = [100 + index * 0.1 for index in range(30)] + [104]
    signal = XauShortScalpStrategy(config).generate_signal(candles(values))
    assert signal.action == SignalAction.OPEN_LONG
    assert signal.take_profit == 104.364
    assert signal.stop_loss == 103.74
