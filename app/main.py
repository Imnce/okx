from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.backtest import BacktestReport, evaluate_candidates
from app.bot import TradingBot
from app.config import get_settings
from app.market_data import fetch_okx_history_candles
from app.models import StrategyConfig
from app.okx_client import OkxClient
from app.presets import xau_short_scalp_preset
from app.storage import AuditStore


settings = get_settings()
store = AuditStore(settings.database_path)
okx_client = OkxClient(settings)
bot = TradingBot(
    config=StrategyConfig(symbol=settings.default_symbol),
    okx=okx_client,
    store=store,
    env=settings.okx_env,
    has_credentials=settings.has_okx_credentials,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await store.init()
    yield
    await okx_client.close()


app = FastAPI(title="OKX Quant Console", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'"
    return response


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/api/status")
async def status():
    return bot.status()


@app.get("/api/config")
async def get_config():
    return bot.config


@app.put("/api/config")
async def update_config(config: StrategyConfig):
    try:
        await bot.update_config(config)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return bot.config


@app.post("/api/start")
async def start():
    try:
        await bot.start()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return bot.status()


@app.post("/api/pause")
async def pause():
    await bot.pause()
    return bot.status()


@app.post("/api/emergency-stop")
async def emergency_stop():
    await bot.emergency_stop()
    return bot.status()


@app.post("/api/close-positions")
async def close_positions():
    await bot.close_positions()
    return bot.status()


@app.get("/api/backtest/xau", response_model=BacktestReport)
async def backtest_xau(bar: str = "1H", limit: int = 300):
    candles = await fetch_okx_history_candles("XAU-USDT-SWAP", bar=bar, limit=limit)
    if len(candles) < 120:
        raise HTTPException(status_code=422, detail="Not enough candles for conservative train/test backtest")
    return evaluate_candidates("XAU-USDT-SWAP", bar, candles)


@app.post("/api/presets/xau-short-scalp")
async def apply_xau_short_scalp_preset():
    config = xau_short_scalp_preset()
    try:
        await bot.update_config(config)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return config
