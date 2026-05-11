from app.models import BotState, Position, RiskDecision, SignalAction, StrategyConfig, TradeSignal


class RiskManager:
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.state = BotState.STOPPED
        self.today_pnl_pct = 0.0
        self.consecutive_losses = 0
        self.emergency_stop = False

    def set_config(self, config: StrategyConfig) -> None:
        self.config = config

    def trip_emergency_stop(self) -> None:
        self.emergency_stop = True
        self.state = BotState.EMERGENCY_STOPPED

    def can_open(self, signal: TradeSignal, positions: list[Position]) -> RiskDecision:
        if self.emergency_stop or self.state == BotState.EMERGENCY_STOPPED:
            return RiskDecision(allowed=False, reason="emergency_stop_active", reduce_only=True)
        if self.state != BotState.RUNNING:
            return RiskDecision(allowed=False, reason=f"bot_not_running:{self.state.value}")
        if signal.action == SignalAction.HOLD:
            return RiskDecision(allowed=False, reason="no_trade_signal")
        if signal.take_profit is None or signal.stop_loss is None:
            return RiskDecision(allowed=False, reason="missing_required_tp_sl")
        if self.config.leverage > 5:
            return RiskDecision(allowed=False, reason="leverage_exceeds_v1_limit")
        if len(positions) >= self.config.max_positions:
            return RiskDecision(allowed=False, reason="max_positions_reached")
        if self.today_pnl_pct <= -abs(self.config.daily_loss_limit_pct):
            return RiskDecision(allowed=False, reason="daily_loss_limit_reached", reduce_only=True)
        if self.consecutive_losses >= self.config.max_consecutive_losses:
            return RiskDecision(allowed=False, reason="consecutive_loss_limit_reached", reduce_only=True)
        return RiskDecision(allowed=True, reason="approved")

