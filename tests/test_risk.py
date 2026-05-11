from app.models import BotState, SignalAction, StrategyConfig, TradeSignal
from app.risk import RiskManager


def signal():
    return TradeSignal(action=SignalAction.OPEN_LONG, symbol="BTC-USDT-SWAP", price=100, take_profit=101, stop_loss=99, reason="test")


def test_risk_blocks_when_not_running():
    risk = RiskManager(StrategyConfig())
    decision = risk.can_open(signal(), [])
    assert not decision.allowed
    assert "bot_not_running" in decision.reason


def test_risk_allows_valid_trade_when_running():
    risk = RiskManager(StrategyConfig())
    risk.state = BotState.RUNNING
    decision = risk.can_open(signal(), [])
    assert decision.allowed


def test_risk_blocks_without_tp_sl():
    risk = RiskManager(StrategyConfig())
    risk.state = BotState.RUNNING
    bad = TradeSignal(action=SignalAction.OPEN_LONG, symbol="BTC-USDT-SWAP", price=100, reason="test")
    decision = risk.can_open(bad, [])
    assert not decision.allowed
    assert decision.reason == "missing_required_tp_sl"


def test_risk_emergency_stop_blocks_and_reduce_only():
    risk = RiskManager(StrategyConfig())
    risk.state = BotState.RUNNING
    risk.trip_emergency_stop()
    decision = risk.can_open(signal(), [])
    assert not decision.allowed
    assert decision.reduce_only

