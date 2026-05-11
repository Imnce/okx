from app.models import StrategyConfig, StrategyKind


def xau_short_scalp_preset() -> StrategyConfig:
    return StrategyConfig(
        symbol="XAU-USDT-SWAP",
        bar="15m",
        strategy_kind=StrategyKind.XAU_SHORT_SCALP,
        short_window=9,
        long_window=30,
        breakout_window=12,
        mean_window=30,
        mean_reversion_threshold_pct=0.8,
        risk_per_trade_pct=0.3,
        take_profit_pct=0.35,
        stop_loss_pct=0.25,
        leverage=2,
        order_size_contracts=1,
        max_positions=1,
        daily_loss_limit_pct=1.5,
        max_consecutive_losses=2,
    )

