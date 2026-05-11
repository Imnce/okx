from app.models import Candle, SignalAction, StrategyConfig, TradeSignal


def simple_moving_average(values: list[float], window: int) -> float:
    if len(values) < window:
        raise ValueError("not enough values for moving average")
    return sum(values[-window:]) / window


class TrendFollowingStrategy:
    def __init__(self, config: StrategyConfig):
        self.config = config

    def generate_signal(self, candles: list[Candle]) -> TradeSignal:
        needed = self.config.long_window
        if len(candles) < needed:
            return TradeSignal(
                action=SignalAction.HOLD,
                symbol=self.config.symbol,
                price=candles[-1].close if candles else 0,
                reason="waiting_for_more_candles",
            )

        closes = [c.close for c in candles]
        short_ma = simple_moving_average(closes, self.config.short_window)
        long_ma = simple_moving_average(closes, self.config.long_window)
        price = closes[-1]

        if short_ma > long_ma:
            return TradeSignal(
                action=SignalAction.OPEN_LONG,
                symbol=self.config.symbol,
                price=price,
                reason=f"short_ma {short_ma:.4f} > long_ma {long_ma:.4f}",
                take_profit=round(price * (1 + self.config.take_profit_pct / 100), 6),
                stop_loss=round(price * (1 - self.config.stop_loss_pct / 100), 6),
            )
        if short_ma < long_ma:
            return TradeSignal(
                action=SignalAction.OPEN_SHORT,
                symbol=self.config.symbol,
                price=price,
                reason=f"short_ma {short_ma:.4f} < long_ma {long_ma:.4f}",
                take_profit=round(price * (1 - self.config.take_profit_pct / 100), 6),
                stop_loss=round(price * (1 + self.config.stop_loss_pct / 100), 6),
            )
        return TradeSignal(action=SignalAction.HOLD, symbol=self.config.symbol, price=price, reason="flat_trend")

