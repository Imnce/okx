from fastapi.testclient import TestClient

from app.main import app


def test_status_endpoint_returns_runtime_state():
    with TestClient(app) as client:
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["env"] == "demo"
        assert data["symbol"].endswith("-SWAP")


def test_config_validation_rejects_bad_windows():
    with TestClient(app) as client:
        response = client.put(
            "/api/config",
            json={
                "symbol": "BTC-USDT-SWAP",
                "bar": "1m",
                "short_window": 10,
                "long_window": 5,
                "risk_per_trade_pct": 0.5,
                "take_profit_pct": 1.2,
                "stop_loss_pct": 0.6,
                "leverage": 3,
                "order_size_contracts": 1,
                "max_positions": 1,
                "daily_loss_limit_pct": 3,
                "max_consecutive_losses": 3,
            },
        )
        assert response.status_code == 422


def test_xau_short_scalp_preset_endpoint_applies_config():
    with TestClient(app) as client:
        response = client.post("/api/presets/xau-short-scalp")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "XAU-USDT-SWAP"
        assert data["bar"] == "15m"
        assert data["strategy_kind"] == "xau_short_scalp"
        assert data["take_profit_pct"] == 0.35
