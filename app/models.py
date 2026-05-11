from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class BotState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    EMERGENCY_STOPPED = "emergency_stopped"


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class SignalAction(str, Enum):
    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"
    HOLD = "hold"


class StrategyKind(str, Enum):
    TREND = "trend"
    BREAKOUT = "breakout"
    MEAN_REVERSION = "mean_reversion"
    XAU_SHORT_SCALP = "xau_short_scalp"


class StrategyConfig(BaseModel):
    symbol: str = "BTC-USDT-SWAP"
    bar: str = "1m"
    strategy_kind: StrategyKind = StrategyKind.TREND
    short_window: int = Field(default=9, ge=2, le=200)
    long_window: int = Field(default=21, ge=3, le=500)
    breakout_window: int = Field(default=24, ge=5, le=240)
    mean_window: int = Field(default=30, ge=5, le=240)
    mean_reversion_threshold_pct: float = Field(default=0.8, gt=0, le=10)
    risk_per_trade_pct: float = Field(default=0.5, gt=0, le=5)
    take_profit_pct: float = Field(default=1.2, gt=0, le=20)
    stop_loss_pct: float = Field(default=0.6, gt=0, le=10)
    leverage: int = Field(default=3, ge=1, le=5)
    order_size_contracts: float = Field(default=1, gt=0)
    max_positions: int = Field(default=1, ge=1, le=5)
    daily_loss_limit_pct: float = Field(default=3, gt=0, le=20)
    max_consecutive_losses: int = Field(default=3, ge=1, le=20)

    @field_validator("long_window")
    @classmethod
    def long_window_must_exceed_short(cls, value: int, info) -> int:
        short_window = info.data.get("short_window")
        if short_window is not None and value <= short_window:
            raise ValueError("long_window must be greater than short_window")
        return value


class Candle(BaseModel):
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0


class TradeSignal(BaseModel):
    action: SignalAction
    symbol: str
    price: float
    reason: str
    take_profit: float | None = None
    stop_loss: float | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RiskDecision(BaseModel):
    allowed: bool
    reason: str
    reduce_only: bool = False


class Position(BaseModel):
    symbol: str
    side: Literal["long", "short"]
    size: float
    entry_price: float
    unrealized_pnl: float = 0


class OrderRequest(BaseModel):
    symbol: str
    side: Side
    size: float
    price: float | None = None
    take_profit: float
    stop_loss: float
    leverage: int
    reduce_only: bool = False


class OrderResult(BaseModel):
    ok: bool
    order_id: str | None = None
    message: str = ""


class RuntimeStatus(BaseModel):
    state: BotState
    env: str
    has_credentials: bool
    symbol: str
    latest_price: float | None = None
    today_pnl_pct: float = 0
    consecutive_losses: int = 0
    positions: list[Position] = Field(default_factory=list)
    open_orders: list[dict] = Field(default_factory=list)
    last_signal: TradeSignal | None = None
    risk_status: str = "ready"
    connection_status: str = "idle"
