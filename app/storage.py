import json
from pathlib import Path
from typing import Any

import aiosqlite

from app.models import StrategyConfig, TradeSignal


SCHEMA = """
CREATE TABLE IF NOT EXISTS config_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  config_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  symbol TEXT NOT NULL,
  action TEXT NOT NULL,
  price REAL NOT NULL,
  reason TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  okx_order_id TEXT,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  size REAL NOT NULL,
  status TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS risk_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reason TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS system_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  level TEXT NOT NULL,
  message TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
"""


class AuditStore:
    def __init__(self, path: Path):
        self.path = path

    async def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    async def save_config(self, config: StrategyConfig) -> None:
        await self._execute("INSERT INTO config_snapshots (config_json) VALUES (?)", config.model_dump_json())

    async def save_signal(self, signal: TradeSignal) -> None:
        await self._execute(
            "INSERT INTO signals (symbol, action, price, reason, payload_json) VALUES (?, ?, ?, ?, ?)",
            signal.symbol,
            signal.action.value,
            signal.price,
            signal.reason,
            signal.model_dump_json(),
        )

    async def save_risk_event(self, reason: str, payload: dict[str, Any]) -> None:
        await self._execute("INSERT INTO risk_events (reason, payload_json) VALUES (?, ?)", reason, json.dumps(payload))

    async def save_order(self, symbol: str, side: str, size: float, status: str, payload: dict[str, Any], okx_order_id: str | None = None) -> None:
        await self._execute(
            "INSERT INTO orders (okx_order_id, symbol, side, size, status, payload_json) VALUES (?, ?, ?, ?, ?, ?)",
            okx_order_id,
            symbol,
            side,
            size,
            status,
            json.dumps(payload),
        )

    async def log(self, level: str, message: str, payload: dict[str, Any] | None = None) -> None:
        await self._execute("INSERT INTO system_logs (level, message, payload_json) VALUES (?, ?, ?)", level, message, json.dumps(payload or {}))

    async def _execute(self, sql: str, *params: Any) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(sql, params)
            await db.commit()

