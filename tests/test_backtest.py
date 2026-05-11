from datetime import datetime, timedelta, timezone

from app.backtest import evaluate_candidates, run_strategy_backtest
from app.models import Candle, StrategyConfig, StrategyKind


def candles(values):
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        Candle(ts=base + timedelta(hours=index), open=value, high=value * 1.001, low=value * 0.999, close=value)
        for index, value in enumerate(values)
    ]


def test_backtest_returns_metrics_without_parameter_search():
    data = candles([100 + index * 0.4 for index in range(80)])
    config = StrategyConfig(strategy_kind=StrategyKind.TREND, short_window=3, long_window=8)
    metrics = run_strategy_backtest(config, data)
    assert metrics.trades > 0
    assert metrics.total_return_pct != 0


def test_evaluate_candidates_uses_train_and_test_segments():
    values = [100 + index * 0.1 for index in range(180)]
    report = evaluate_candidates("XAU-USDT-SWAP", "1H", candles(values))
    assert report.symbol == "XAU-USDT-SWAP"
    assert len(report.candidates) == 5
    assert all(candidate.train.trades >= 0 and candidate.test.trades >= 0 for candidate in report.candidates)
