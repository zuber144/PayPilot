"""PayPal Orders API v2 client with token caching and deterministic mock mode."""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.config import settings


class PayPalError(Exception):
    """Raised when a PayPal API call fails or returns an unexpected payload."""


# Token cache: (access_token, expires_at_monotonic)
_token_cache: tuple[str, float] | None = None
_mock_orders: dict[str, tuple[str, str]] = {}


def clear_token_cache() -> None:
    global _token_cache
    _token_cache = None


def minor_to_str(amount_minor: int) -> str:
    """Convert integer minor units (e.g. cents) to 2-decimal string without floats."""
    if not isinstance(amount_minor, int) or isinstance(amount_minor, bool) or amount_minor < 0:
        raise ValueError(f"Invalid minor amount: {amount_minor!r}")
    whole, cents = divmod(amount_minor, 100)
    return f"{whole}.{cents:02d}"


def str_to_minor(amount_str: str) -> int:
    """Parse a decimal currency string (e.g. '41000.00' or '41000') into integer minor units without floats."""
    s = amount_str.strip()
    if not s or s.startswith("-"):
        raise PayPalError(f"Invalid amount string from PayPal: {amount_str!r}")
    parts = s.split(".")
    if len(parts) == 1:
        if not parts[0].isdigit():
            raise PayPalError(f"Invalid amount string from PayPal: {amount_str!r}")
        return int(parts[0]) * 100
    if len(parts) == 2:
        whole_s, frac_s = parts
        if not whole_s.isdigit() or not frac_s.isdigit() or len(frac_s) > 2:
            raise PayPalError(f"Invalid amount string from PayPal: {amount_str!r}")
        frac_padded = frac_s.ljust(2, "0")
        return int(whole_s) * 100 + int(frac_padded)
    raise PayPalError(f"Invalid amount string from PayPal: {amount_str!r}")


def _is_mock() -> bool:
    return settings.PAYPAL_MODE == "mock"


def get_access_token() -> str:
    """Fetch or return cached OAuth2 client-credentials token."""
    global _token_cache
    if _is_mock():
        return "MOCK-ACCESS-TOKEN"

    now = time.monotonic()
    if _token_cache is not None:
        token, expires_at = _token_cache
        if now < expires_at:
            return token

    if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_CLIENT_SECRET:
        raise PayPalError("PayPal credentials are not configured")

    url = f"{settings.PAYPAL_BASE_URL.rstrip('/')}/v1/oauth2/token"
    try:
        with httpx.Client(timeout=settings.PAYPAL_TIMEOUT_SECONDS) as client:
            resp = client.post(
                url,
                auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
                data={"grant_type": "client_credentials"},
                headers={"Accept": "application/json"},
            )
    except httpx.HTTPError as exc:
        raise PayPalError(f"PayPal OAuth request failed: {exc}") from exc

    if resp.status_code >= 400:
        raise PayPalError(f"PayPal OAuth failed with status {resp.status_code}")

    try:
        data: dict[str, Any] = resp.json()
        access_token = str(data["access_token"])
        expires_in = int(data.get("expires_in", 3600))
    except (ValueError, KeyError, TypeError) as exc:
        raise PayPalError("Invalid OAuth response from PayPal") from exc

    _token_cache = (access_token, now + max(expires_in - 60, 0))
    return access_token


def create_order(
    amount_str: str,
    currency: str,
    return_url: str,
    cancel_url: str,
    request_id: str,
) -> dict[str, Any]:
    """Create a PayPal order with intent CAPTURE."""
    if _is_mock():
        order_id = f"MOCK-{request_id}"
        _mock_orders[order_id] = (amount_str, currency)
        approval_url = f"{settings.FRONTEND_URL.rstrip('/')}/payments/return?token={order_id}"
        return {
            "id": order_id,
            "status": "CREATED",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": currency,
                        "value": amount_str,
                    }
                }
            ],
            "links": [
                {"rel": "approve", "href": approval_url, "method": "GET"},
                {"rel": "self", "href": f"https://mock.paypal.local/v2/checkout/orders/{order_id}", "method": "GET"},
            ],
        }

    token = get_access_token()
    url = f"{settings.PAYPAL_BASE_URL.rstrip('/')}/v2/checkout/orders"
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": currency,
                    "value": amount_str,
                }
            }
        ],
        "application_context": {
            "return_url": return_url,
            "cancel_url": cancel_url,
        },
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "PayPal-Request-Id": request_id,
    }
    try:
        with httpx.Client(timeout=settings.PAYPAL_TIMEOUT_SECONDS) as client:
            resp = client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise PayPalError(f"PayPal create_order request failed: {exc}") from exc

    if resp.status_code >= 400:
        raise PayPalError(f"PayPal create_order failed with status {resp.status_code}: {resp.text}")

    try:
        data: dict[str, Any] = resp.json()
    except ValueError as exc:
        raise PayPalError("Invalid JSON from PayPal create_order") from exc

    if "id" not in data:
        raise PayPalError("PayPal create_order response missing order id")
    return data


def capture_order(order_id: str, request_id: str | None = None) -> dict[str, Any]:
    """Capture an approved PayPal order."""
    req_id = request_id or f"capture-{order_id}"
    if _is_mock():
        capture_id = f"MOCK-CAP-{order_id}"
        res: dict[str, Any] = {
            "id": order_id,
            "status": "COMPLETED",
        }
        if order_id in _mock_orders:
            amt_str, curr = _mock_orders[order_id]
            res["purchase_units"] = [
                {
                    "payments": {
                        "captures": [
                            {
                                "id": capture_id,
                                "status": "COMPLETED",
                                "amount": {
                                    "currency_code": curr,
                                    "value": amt_str,
                                },
                            }
                        ]
                    }
                }
            ]
        else:
            res["purchase_units"] = [
                {
                    "payments": {
                        "captures": [
                            {
                                "id": capture_id,
                                "status": "COMPLETED",
                            }
                        ]
                    }
                }
            ]
        return res

    token = get_access_token()
    url = f"{settings.PAYPAL_BASE_URL.rstrip('/')}/v2/checkout/orders/{order_id}/capture"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "PayPal-Request-Id": req_id,
    }
    try:
        with httpx.Client(timeout=settings.PAYPAL_TIMEOUT_SECONDS) as client:
            resp = client.post(url, content=b"{}", headers=headers)
    except httpx.HTTPError as exc:
        raise PayPalError(f"PayPal capture_order request failed: {exc}") from exc

    if resp.status_code >= 400:
        raise PayPalError(f"PayPal capture_order failed with status {resp.status_code}: {resp.text}")

    try:
        data: dict[str, Any] = resp.json()
    except ValueError as exc:
        raise PayPalError("Invalid JSON from PayPal capture_order") from exc

    return data


def get_order(order_id: str) -> dict[str, Any]:
    """Retrieve a PayPal order by ID."""
    if _is_mock():
        res: dict[str, Any] = {
            "id": order_id,
            "status": "APPROVED",
        }
        if order_id in _mock_orders:
            amt_str, curr = _mock_orders[order_id]
            res["purchase_units"] = [
                {
                    "amount": {
                        "currency_code": curr,
                        "value": amt_str,
                    }
                }
            ]
        return res

    token = get_access_token()
    url = f"{settings.PAYPAL_BASE_URL.rstrip('/')}/v2/checkout/orders/{order_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    try:
        with httpx.Client(timeout=settings.PAYPAL_TIMEOUT_SECONDS) as client:
            resp = client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise PayPalError(f"PayPal get_order request failed: {exc}") from exc

    if resp.status_code >= 400:
        raise PayPalError(f"PayPal get_order failed with status {resp.status_code}: {resp.text}")

    try:
        data: dict[str, Any] = resp.json()
    except ValueError as exc:
        raise PayPalError("Invalid JSON from PayPal get_order") from exc

    return data
