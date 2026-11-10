"""Settings and hard limits. All loops must be bounded by values defined here."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Infrastructure
    DATABASE_URL: str = "sqlite:///./agentos.db"  # docker-compose Postgres: see .env.example
    FRONTEND_URL: str = "http://localhost:5173"

    # LLM. "mock" (default) never touches the network; "live" requires OPENAI_API_KEY.
    LLM_MODE: Literal["mock", "live"] = "mock"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: float = 20.0
    LLM_RETRIES: int = 1

    # PayPal. "mock" (default) never touches the network; "sandbox" requires credentials.
    PAYPAL_MODE: Literal["mock", "sandbox"] = "mock"
    PAYPAL_CLIENT_ID: str = ""
    PAYPAL_CLIENT_SECRET: str = ""
    PAYPAL_BASE_URL: str = "https://api-m.sandbox.paypal.com"
    PAYPAL_TIMEOUT_SECONDS: float = 20.0
    PAYMENTS_ENABLED: bool = True  # kill switch checked by /pay and /capture

    # Orchestration limits (work-division doc 3.3)
    MAX_DISCOVERY_RETRIES: int = 2
    MAX_NEGOTIATION_ROUNDS: int = 3
    MAX_PLAN_REVISIONS: int = 1
    MAX_GRAPH_STEPS: int = 25
    REQUIRED_COVERAGE: int = 2  # verified candidates wanted per need
    MIN_COVERAGE: int = 1  # continue_with_minimum allowed only if every need has >= this
    COUNTER_RATIO: float = 0.90  # our counter = 90% of current price
    MAX_PLAN_COMBINATIONS: int = 10_000  # cap for itertools.product enumeration

    # PayGuard thresholds (work-division doc 3.5)
    MAX_TXN_MINOR: int = 10_000_000  # INR 1,00,000.00
    HIGH_RISK_THRESHOLD: float = 0.7
    MEDIUM_RISK_THRESHOLD: float = 0.4
    SINGLE_VENDOR_SHARE_MAX: float = 0.70
    SUPPORTED_CURRENCIES: list[str] = ["INR", "USD"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
