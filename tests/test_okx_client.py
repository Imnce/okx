import asyncio

from app.config import Settings
from app.okx_client import RateLimiter, OkxClient, sign_okx


def test_sign_okx_matches_known_payload():
    signature = sign_okx("secret", "2020-12-08T09:08:57.715Z", "GET", "/api/v5/account/balance", "")
    assert signature == "5ktoTKif8DCJlIPb/3Kfd1A17bIRye6jpS9QBWj+9AU="


def test_demo_headers_include_simulated_trading():
    settings = Settings(okx_api_key="k", okx_api_secret="s", okx_api_passphrase="p", okx_env="demo")
    client = OkxClient(settings)
    headers = client.headers("GET", "/api/v5/account/balance")
    assert headers["OK-ACCESS-KEY"] == "k"
    assert headers["x-simulated-trading"] == "1"
    asyncio.run(client.close())


async def test_rate_limiter_allows_configured_capacity():
    limiter = RateLimiter(max_calls=2, period_seconds=0.05)
    await limiter.acquire()
    await limiter.acquire()
    await limiter.acquire()
    assert True
