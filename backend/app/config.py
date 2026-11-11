"""Settings and hard limits. All loops must be bounded by values defined here."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Infrastructure
    DATABASE_URL: str = "sqlite:///./agentos.db"  # docker-compose Postgres: see .env.example
    FRONTEND_URL: str = "http://localhost:5173"

    # LLM. "mock" (default) never touches the network; "live" requires the selected
    # provider's API key (falls back to mock if it is missing).
    LLM_MODE: Literal["mock", "live"] = "mock"
    LLM_PROVIDER: Literal["anthropic", "openai"] = "anthropic"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-haiku-5-5"
    ANTHROPIC_EFFORT: Literal["low", "medium", "high"] = "low"
    ANTHROPIC_MAX_TOKENS: int = 4096
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

    # Product search. "mock" (default) reads the seeded offline catalog and never touches the
    # network; "live" scrapes the allowlisted store search pages and falls back to the catalog
    # (FALLBACK trace) on any fetch/parse failure. Prices are parsed in code, never by the LLM.
    SEARCH_MODE: Literal["mock", "live"] = "mock"
    SEARCH_STORES: list[str] = ["amazon", "flipkart"]
    SEARCH_ALLOWED_HOSTS: list[str] = ["www.amazon.in", "amazon.in", "www.flipkart.com", "flipkart.com"]
    SEARCH_TIMEOUT_SECONDS: float = 10.0
    SEARCH_MAX_BYTES: int = 3_000_000  # response size cap per page
    SEARCH_MAX_REDIRECTS: int = 3  # every hop must stay on SEARCH_ALLOWED_HOSTS
    SEARCH_USER_AGENT: str = "AgentOS-PriceCompare/1.0"  # generic; never contains user details
    MAX_LISTINGS_PER_STORE: int = 5  # per need, per store
    SEARCH_DEFAULT_DELIVERY_DAYS: int = 5  # when a page shows no parseable delivery date

    # Display currency vs charge currency. Listings are priced in INR (paise); every pack price and
    # shipping fee is converted to USD cents once, at ingest, with integer ceil division.
    DISPLAY_CURRENCY: str = "INR"
    INR_PAISE_PER_USD: int = 8_400  # fixed demo rate INR 84.00 = USD 1.00 (no live FX call)

    # Seller verification (derived in code, never relaxed by the orchestrator)
    VERIFIED_STORES: list[str] = ["amazon", "flipkart"]
    VERIFIED_MIN_RATING: float = 4.0
    VERIFIED_MIN_REVIEWS: int = 50

    # Orchestration limits (work-division doc 3.3)
    MAX_DISCOVERY_RETRIES: int = 2
    MAX_NEGOTIATION_ROUNDS: int = 1  # price-comparison passes (store prices are fixed)
    MAX_PLAN_REVISIONS: int = 1
    MAX_GRAPH_STEPS: int = 25
    REQUIRED_COVERAGE: int = 2  # verified candidates wanted per need
    MIN_COVERAGE: int = 1  # continue_with_minimum allowed only if every need has >= this
    MAX_PLAN_COMBINATIONS: int = 10_000  # cap for itertools.product enumeration

    # PayGuard thresholds (work-division doc 3.5)
    MAX_TXN_MINOR: int = 10_000_000  # USD 100,000.00 (minor units = cents)
    HIGH_RISK_THRESHOLD: float = 0.7
    MEDIUM_RISK_THRESHOLD: float = 0.4
    SINGLE_VENDOR_SHARE_MAX: float = 0.70
    SUPPORTED_CURRENCIES: list[str] = ["USD"]  # PayPal Sandbox rejects INR (CURRENCY_NOT_SUPPORTED)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

