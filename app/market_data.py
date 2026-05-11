from datetime import datetime, timezone

import httpx

from app.models import Candle


async def fetch_okx_history_candles(inst_id: str, bar: str = "1H", limit: int = 300) -> list[Candle]:
    params = {"instId": inst_id, "bar": bar, "limit": str(min(limit, 300))}
    async with httpx.AsyncClient(base_url="https://www.okx.com", timeout=12) as client:
        response = await client.get("/api/v5/market/history-candles", params=params)
        response.raise_for_status()
    data = response.json()
    if data.get("code") != "0":
        raise ValueError(data.get("msg") or f"OKX candle error: {data}")

    candles: list[Candle] = []
    for row in data.get("data", []):
        ts_ms, open_, high, low, close, volume = row[:6]
        candles.append(
            Candle(
                ts=datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc),
                open=float(open_),
                high=float(high),
                low=float(low),
                close=float(close),
                volume=float(volume),
            )
        )
    return list(reversed(candles))

