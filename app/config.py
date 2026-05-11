from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    okx_env: Literal["demo", "live"] = "demo"
    okx_api_key: str = ""
    okx_api_secret: str = ""
    okx_api_passphrase: str = ""
    database_path: Path = Field(default=Path("data/okx_quant.db"))
    default_symbol: str = "BTC-USDT-SWAP"
    allow_live_trading: bool = False

    @property
    def rest_base_url(self) -> str:
        return "https://www.okx.com"

    @property
    def is_demo(self) -> bool:
        return self.okx_env == "demo"

    @property
    def has_okx_credentials(self) -> bool:
        return bool(self.okx_api_key and self.okx_api_secret and self.okx_api_passphrase)


@lru_cache
def get_settings() -> Settings:
    return Settings()

