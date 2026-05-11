import asyncio
from datetime import datetime, timezone

from app.models import BotState, Candle, OrderRequest, Position, RuntimeStatus, Side, SignalAction, StrategyConfig
from app.okx_client import OkxApiError, OkxClient
from app.risk import RiskManager
from app.storage import AuditStore
from app.strategy import build_strategy


class TradingBot:
    def __init__(self, config: StrategyConfig, okx: OkxClient, store: AuditStore, env: str, has_credentials: bool):
        self.config = config
        self.okx = okx
        self.store = store
        self.env = env
        self.has_credentials = has_credentials
        self.risk = RiskManager(config)
        self.strategy = build_strategy(config)
        self.state = BotState.STOPPED
        self.latest_price: float | None = None
        self.positions: list[Position] = []
        self.open_orders: list[dict] = []
        self.last_signal = None
        self.connection_status = "idle"
        self._task: asyncio.Task | None = None
        self._candles: list[Candle] = []

    async def start(self) -> None:
        if self.state == BotState.EMERGENCY_STOPPED:
            raise ValueError("emergency stop is active; restart the app to clear it")
        self.state = BotState.RUNNING
        self.risk.state = BotState.RUNNING
        await self.store.save_config(self.config)
        await self.store.log("info", "bot_started", {"symbol": self.config.symbol})
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    async def pause(self) -> None:
        self.state = BotState.PAUSED
        self.risk.state = BotState.PAUSED
        await self.store.log("info", "bot_paused")

    async def emergency_stop(self) -> None:
        self.state = BotState.EMERGENCY_STOPPED
        self.risk.trip_emergency_stop()
        await self.store.save_risk_event("emergency_stop", {"symbol": self.config.symbol})

    async def update_config(self, config: StrategyConfig) -> None:
        if self.state == BotState.RUNNING:
            raise ValueError("pause the bot before changing strategy config")
        self.config = config
        self.risk.set_config(config)
        self.strategy = build_strategy(config)
        await self.store.save_config(config)

    async def close_positions(self) -> None:
        self.positions.clear()
        self.open_orders.clear()
        await self.store.log("warning", "manual_close_positions_requested")

    def status(self) -> RuntimeStatus:
        return RuntimeStatus(
            state=self.state,
            env=self.env,
            has_credentials=self.has_credentials,
            symbol=self.config.symbol,
            latest_price=self.latest_price,
            today_pnl_pct=self.risk.today_pnl_pct,
            consecutive_losses=self.risk.consecutive_losses,
            positions=self.positions,
            open_orders=self.open_orders,
            last_signal=self.last_signal,
            risk_status="emergency_stop" if self.risk.emergency_stop else "ready",
            connection_status=self.connection_status,
        )

    async def run_once_with_candles(self, candles: list[Candle]) -> None:
        self._candles = candles
        if candles:
            self.latest_price = candles[-1].close
        signal = self.strategy.generate_signal(candles)
        self.last_signal = signal
        await self.store.save_signal(signal)
        decision = self.risk.can_open(signal, self.positions)
        if not decision.allowed:
            await self.store.save_risk_event(decision.reason, {"signal": signal.model_dump(mode="json")})
            return
        order = self._build_order(signal)
        try:
            result = await self.okx.place_order(order)
            await self.store.save_order(order.symbol, order.side.value, order.size, "submitted", order.model_dump(mode="json"), result.order_id)
            self.open_orders.append({"id": result.order_id, "symbol": order.symbol, "side": order.side.value, "size": order.size})
        except OkxApiError as exc:
            await self.store.log("error", "okx_order_failed", {"error": str(exc)})

    def _build_order(self, signal) -> OrderRequest:
        if signal.action == SignalAction.OPEN_LONG:
            side = Side.BUY
        elif signal.action == SignalAction.OPEN_SHORT:
            side = Side.SELL
        else:
            raise ValueError("cannot build order for hold signal")
        if signal.take_profit is None or signal.stop_loss is None:
            raise ValueError("TP/SL is required")
        return OrderRequest(
            symbol=signal.symbol,
            side=side,
            size=self.config.order_size_contracts,
            take_profit=signal.take_profit,
            stop_loss=signal.stop_loss,
            leverage=self.config.leverage,
        )

    async def _loop(self) -> None:
        self.connection_status = "running_local_loop"
        while self.state == BotState.RUNNING:
            await asyncio.sleep(5)
            if not self._candles:
                now = datetime.now(timezone.utc)
                price = self.latest_price or 100.0
                self._candles.append(Candle(ts=now, open=price, high=price, low=price, close=price))
            window = max(self.config.long_window, self.config.breakout_window + 1, self.config.mean_window)
            await self.run_once_with_candles(self._candles[-window:])
