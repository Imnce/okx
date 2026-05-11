import asyncio
import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import Settings
from app.models import OrderRequest, OrderResult, Side


class OkxApiError(RuntimeError):
    pass


def okx_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sign_okx(secret: str, timestamp: str, method: str, request_path: str, body: str = "") -> str:
    payload = f"{timestamp}{method.upper()}{request_path}{body}"
    digest = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


class RateLimiter:
    def __init__(self, max_calls: int, period_seconds: float):
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self._calls: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                loop_time = asyncio.get_running_loop().time()
                self._calls = [t for t in self._calls if loop_time - t < self.period_seconds]
                if len(self._calls) < self.max_calls:
                    self._calls.append(loop_time)
                    return
                wait_for = self.period_seconds - (loop_time - self._calls[0])
            await asyncio.sleep(max(wait_for, 0.01))


class OkxClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._limiter = RateLimiter(max_calls=60, period_seconds=2)
        self._client = httpx.AsyncClient(base_url=settings.rest_base_url, timeout=10)

    async def close(self) -> None:
        await self._client.aclose()

    def headers(self, method: str, path: str, body: str = "") -> dict[str, str]:
        ts = okx_timestamp()
        headers = {
            "OK-ACCESS-KEY": self.settings.okx_api_key,
            "OK-ACCESS-SIGN": sign_okx(self.settings.okx_api_secret, ts, method, path, body),
            "OK-ACCESS-TIMESTAMP": ts,
            "OK-ACCESS-PASSPHRASE": self.settings.okx_api_passphrase,
            "Content-Type": "application/json",
        }
        if self.settings.is_demo:
            headers["x-simulated-trading"] = "1"
        return headers

    async def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.settings.okx_env == "live" and not self.settings.allow_live_trading:
            raise OkxApiError("Live trading is disabled by configuration")
        if not self.settings.has_okx_credentials:
            raise OkxApiError("OKX credentials are missing")

        body = json.dumps(payload, separators=(",", ":")) if payload else ""
        await self._limiter.acquire()
        response = await self._client.request(method, path, content=body or None, headers=self.headers(method, path, body))
        response.raise_for_status()
        data = response.json()
        if data.get("code") != "0":
            raise OkxApiError(data.get("msg") or f"OKX error: {data}")
        return data

    async def place_order(self, order: OrderRequest) -> OrderResult:
        side = "buy" if order.side == Side.BUY else "sell"
        payload: dict[str, Any] = {
            "instId": order.symbol,
            "tdMode": "isolated",
            "side": side,
            "ordType": "market" if order.price is None else "limit",
            "sz": str(order.size),
            "lever": str(order.leverage),
            "reduceOnly": "true" if order.reduce_only else "false",
            "attachAlgoOrds": [
                {
                    "tpTriggerPx": str(order.take_profit),
                    "tpOrdPx": "-1",
                    "slTriggerPx": str(order.stop_loss),
                    "slOrdPx": "-1",
                }
            ],
        }
        if order.price is not None:
            payload["px"] = str(order.price)
        data = await self.request("POST", "/api/v5/trade/order", payload)
        order_id = (data.get("data") or [{}])[0].get("ordId")
        return OrderResult(ok=True, order_id=order_id, message="submitted")

    async def get_account_balance(self) -> dict[str, Any]:
        return await self.request("GET", "/api/v5/account/balance")

    async def cancel_all_after(self, timeout_ms: int = 0) -> dict[str, Any]:
        return await self.request("POST", "/api/v5/trade/cancel-all-after", {"timeOut": str(timeout_ms)})

