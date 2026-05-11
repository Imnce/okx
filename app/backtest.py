from dataclasses import dataclass
from math import sqrt

from pydantic import BaseModel

from app.models import Candle, SignalAction, StrategyConfig, StrategyKind
from app.strategy import build_strategy


class BacktestMetrics(BaseModel):
    trades: int
    win_rate_pct: float
    total_return_pct: float
    max_drawdown_pct: float
    profit_factor: float
    score: float


class StrategyCandidateResult(BaseModel):
    name: str
    config: StrategyConfig
    train: BacktestMetrics
    test: BacktestMetrics
    anti_overfit_note: str


class BacktestReport(BaseModel):
    symbol: str
    bar: str
    candles: int
    candidates: list[StrategyCandidateResult]
    recommendation: StrategyCandidateResult | None


@dataclass
class Trade:
    pnl_pct: float


def candidate_configs(symbol: str, bar: str) -> list[tuple[str, StrategyConfig]]:
    base = dict(symbol=symbol, bar=bar, leverage=2, risk_per_trade_pct=0.5, order_size_contracts=1, max_positions=1)
    return [
        ("XAU slow trend", StrategyConfig(**base, strategy_kind=StrategyKind.TREND, short_window=12, long_window=48, take_profit_pct=1.4, stop_loss_pct=0.7)),
        ("XAU balanced trend", StrategyConfig(**base, strategy_kind=StrategyKind.TREND, short_window=9, long_window=30, take_profit_pct=1.1, stop_loss_pct=0.65)),
        ("XAU range breakout", StrategyConfig(**base, strategy_kind=StrategyKind.BREAKOUT, breakout_window=36, take_profit_pct=1.3, stop_loss_pct=0.65)),
        (
            "XAU mean reversion",
            StrategyConfig(
                **base,
                strategy_kind=StrategyKind.MEAN_REVERSION,
                mean_window=36,
                mean_reversion_threshold_pct=0.7,
                take_profit_pct=0.65,
                stop_loss_pct=0.55,
            ),
        ),
    ]


def run_strategy_backtest(config: StrategyConfig, candles: list[Candle], fee_pct: float = 0.05) -> BacktestMetrics:
    strategy = build_strategy(config)
    trades: list[Trade] = []
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    warmup = max(config.long_window, config.breakout_window + 1, config.mean_window)

    for index in range(warmup, len(candles) - 1):
        signal = strategy.generate_signal(candles[: index + 1])
        if signal.action == SignalAction.HOLD:
            continue

        entry = candles[index].close
        exit_price = candles[index + 1].close
        if signal.action == SignalAction.OPEN_LONG:
            raw_pct = (exit_price - entry) / entry * 100
        else:
            raw_pct = (entry - exit_price) / entry * 100

        bounded_pct = min(config.take_profit_pct, max(-config.stop_loss_pct, raw_pct)) - fee_pct
        trades.append(Trade(pnl_pct=bounded_pct))
        equity *= 1 + bounded_pct / 100
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak * 100)

    wins = [t.pnl_pct for t in trades if t.pnl_pct > 0]
    losses = [abs(t.pnl_pct) for t in trades if t.pnl_pct <= 0]
    total_return_pct = (equity - 1) * 100
    profit_factor = sum(wins) / sum(losses) if losses else (sum(wins) if wins else 0)
    win_rate_pct = len(wins) / len(trades) * 100 if trades else 0
    trade_penalty = 0 if len(trades) >= 5 else (5 - len(trades)) * 2
    score = total_return_pct - max_drawdown * 1.8 + min(profit_factor, 3) * 2 - trade_penalty
    if len(trades) > 1:
        avg = sum(t.pnl_pct for t in trades) / len(trades)
        variance = sum((t.pnl_pct - avg) ** 2 for t in trades) / (len(trades) - 1)
        score += avg / (sqrt(variance) + 0.01)

    return BacktestMetrics(
        trades=len(trades),
        win_rate_pct=round(win_rate_pct, 2),
        total_return_pct=round(total_return_pct, 2),
        max_drawdown_pct=round(max_drawdown, 2),
        profit_factor=round(profit_factor, 2),
        score=round(score, 2),
    )


def evaluate_candidates(symbol: str, bar: str, candles: list[Candle]) -> BacktestReport:
    split = max(int(len(candles) * 0.65), 1)
    train_candles = candles[:split]
    test_candles = candles[split:]
    results: list[StrategyCandidateResult] = []

    for name, config in candidate_configs(symbol, bar):
        train = run_strategy_backtest(config, train_candles)
        test = run_strategy_backtest(config, test_candles)
        overfit_gap = train.total_return_pct - test.total_return_pct
        note = "pass: sample-out performance is comparable"
        if train.trades < 5 or test.trades < 3:
            note = "caution: too few trades for high confidence"
        elif overfit_gap > 8 and test.total_return_pct <= 0:
            note = "reject: train/test gap suggests overfitting"
        elif test.max_drawdown_pct > abs(test.total_return_pct) + 3:
            note = "caution: drawdown dominates sample-out return"
        results.append(StrategyCandidateResult(name=name, config=config, train=train, test=test, anti_overfit_note=note))

    ranked = sorted(results, key=lambda item: (item.test.score, item.test.total_return_pct, -item.test.max_drawdown_pct), reverse=True)
    recommendation = ranked[0] if ranked and "reject" not in ranked[0].anti_overfit_note else None
    return BacktestReport(symbol=symbol, bar=bar, candles=len(candles), candidates=ranked, recommendation=recommendation)
