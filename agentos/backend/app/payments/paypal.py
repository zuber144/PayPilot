"""
app/payments/paypal.py — PayPal Orders API v2 integration (Sandbox).

Functions:
  get_access_token()   — OAuth 2.0 client credentials; token cached in module.
  create_order(...)    — CAPTURE intent, amount from minor units → decimal string.
  capture_order(...)   — capture an APPROVED order; returns raw response dict.

Environment variables required:
  PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_BASE_URL, APP_BASE_URL
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Token cache (simple in-process; sufficient for a monolith)
# ---------------------------------------------------------------------------

_token_cache: dict[str, Any] = {
    "access_token": None,
    "expires_at": 0.0,
}


def _minor_to_decimal(minor: int, currency: str) -> str:
    """
    Convert minor units (cents) to a decimal string suitable for PayPal.
    Most currencies have 2 decimal places; JPY and a few others have 0.
    For this scaffold we assume 2 decimal places for all currencies.
    """
    # TODO(payments-owner): add a proper currency → exponent map for JPY, etc.
    return f"{minor / 100:.2f}"


def get_access_token() -> str:
    """Return a valid OAuth 2.0 access token, refreshing if expired."""
    settings = get_settings()
    now = time.time()

    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 30:
        return str(_token_cache["access_token"])

    response = httpx.post(
        f"{settings.paypal_base_url}/v1/oauth2/token",
        auth=(settings.paypal_client_id, settings.paypal_client_secret),
        data={"grant_type": "client_credentials"},
        timeout=15.0,
    )
    response.raise_for_status()
    data = response.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)
    logger.debug("PayPal token refreshed; expires in %ds", data.get("expires_in", 3600))
    return str(_token_cache["access_token"])


def create_order(
    *,
    plan_id: int,
    transaction_id: int,
    amount_minor: int,
    currency: str,
) -> dict[str, Any]:
    """
    Create a PayPal order with CAPTURE intent.
    Returns the raw PayPal API response dict (contains id and approval link).
    """
    settings = get_settings()
    token = get_access_token()
    amount_str = _minor_to_decimal(amount_minor, currency)

    return_url = f"{settings.app_base_url}/payments/return?plan_id={plan_id}"
    cancel_url = f"{settings.app_base_url}/plans/{plan_id}"

    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": str(plan_id),
                "amount": {
                    "currency_code": currency,
                    "value": amount_str,
                },
                "description": f"PayPilot plan #{plan_id}",
            }
        ],
        "application_context": {
            "return_url": return_url,
            "cancel_url": cancel_url,
            "brand_name": "PayPilot AgentOS",
            "user_action": "PAY_NOW",
        },
    }

    response = httpx.post(
        f"{settings.paypal_base_url}/v2/checkout/orders",
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "PayPal-Request-Id": str(transaction_id),
        },
        timeout=20.0,
    )
    response.raise_for_status()
    return dict(response.json())


def capture_order(paypal_order_id: str) -> dict[str, Any]:
    """
    Capture a PayPal order that has been approved by the buyer.
    Returns the raw capture response dict.
    """
    token = get_access_token()
    settings = get_settings()

    response = httpx.post(
        f"{settings.paypal_base_url}/v2/checkout/orders/{paypal_order_id}/capture",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=20.0,
    )
    response.raise_for_status()
    return dict(response.json())
