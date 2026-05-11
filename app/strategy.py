from app.models import Candle, SignalAction, StrategyConfig, StrategyKind, TradeSignal


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


class BreakoutStrategy:
    def __init__(self, config: StrategyConfig):
        self.config = config

    def generate_signal(self, candles: list[Candle]) -> TradeSignal:
        window = self.config.breakout_window
        if len(candles) <= window:
            return TradeSignal(
                action=SignalAction.HOLD,
                symbol=self.config.symbol,
                price=candles[-1].close if candles else 0,
                reason="waiting_for_breakout_window",
            )

        previous = candles[-window - 1 : -1]
        price = candles[-1].close
        prior_high = max(c.high for c in previous)
        prior_low = min(c.low for c in previous)
        if price > prior_high:
            return TradeSignal(
                action=SignalAction.OPEN_LONG,
                symbol=self.config.symbol,
                price=price,
                reason=f"close {price:.4f} broke prior_high {prior_high:.4f}",
                take_profit=round(price * (1 + self.config.take_profit_pct / 100), 6),
                stop_loss=round(price * (1 - self.config.stop_loss_pct / 100), 6),
            )
        if price < prior_low:
            return TradeSignal(
                action=SignalAction.OPEN_SHORT,
                symbol=self.config.symbol,
                price=price,
                reason=f"close {price:.4f} broke prior_low {prior_low:.4f}",
                take_profit=round(price * (1 - self.config.take_profit_pct / 100), 6),
                stop_loss=round(price * (1 + self.config.stop_loss_pct / 100), 6),
            )
        return TradeSignal(action=SignalAction.HOLD, symbol=self.config.symbol, price=price, reason="inside_breakout_range")


class MeanReversionStrategy:
    def __init__(self, config: StrategyConfig):
        self.config = config

    def generate_signal(self, candles: list[Candle]) -> TradeSignal:
        window = self.config.mean_window
        if len(candles) < window:
            return TradeSignal(
                action=SignalAction.HOLD,
                symbol=self.config.symbol,
                price=candles[-1].close if candles else 0,
                reason="waiting_for_mean_window",
            )

        closes = [c.close for c in candles]
        price = closes[-1]
        mean = simple_moving_average(closes, window)
        distance_pct = ((price - mean) / mean) * 100
        threshold = self.config.mean_reversion_threshold_pct
        if distance_pct <= -threshold:
            return TradeSignal(
                action=SignalAction.OPEN_LONG,
                symbol=self.config.symbol,
                price=price,
                reason=f"price {distance_pct:.2f}% below mean",
                take_profit=round(price * (1 + self.config.take_profit_pct / 100), 6),
                stop_loss=round(price * (1 - self.config.stop_loss_pct / 100), 6),
            )
        if distance_pct >= threshold:
            return TradeSignal(
                action=SignalAction.OPEN_SHORT,
                symbol=self.config.symbol,
                price=price,
                reason=f"price {distance_pct:.2f}% above mean",
                take_profit=round(price * (1 - self.config.take_profit_pct / 100), 6),
                stop_loss=round(price * (1 + self.config.stop_loss_pct / 100), 6),
            )
        return TradeSignal(action=SignalAction.HOLD, symbol=self.config.symbol, price=price, reason="near_mean")


def build_strategy(config: StrategyConfig):
    if config.strategy_kind == StrategyKind.BREAKOUT:
        return BreakoutStrategy(config)
    if config.strategy_kind == StrategyKind.MEAN_REVERSION:
        return MeanReversionStrategy(config)
    return TrendFollowingStrategy(config)
