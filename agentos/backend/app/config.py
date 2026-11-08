"""
app/config.py — all settings loaded from environment / .env file.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql://agentos:agentos_secret@localhost:5432/agentos"

    # PayPal
    paypal_client_id: str = "SANDBOX_CLIENT_ID"
    paypal_client_secret: str = "SANDBOX_CLIENT_SECRET"
    paypal_base_url: str = "https://api-m.sandbox.paypal.com"
    app_base_url: str = "http://localhost:5173"

    # LLM
    llm_provider: str = "stub"
    llm_model: str = "stub-v1"
    llm_api_key: str = ""

    # PayGuard
    max_txn_minor: int = 1_000_000  # 10 000.00 USD in cents

    # CORS
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split() if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
