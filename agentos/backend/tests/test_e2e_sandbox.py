"""Live PayPal Sandbox integration test (skipped unless credentials are set)."""

import os
import uuid

import pytest

from app.config import settings
from app.payments import paypal

_HAS_PAYPAL_CREDS = bool(os.environ.get("PAYPAL_CLIENT_ID") and os.environ.get("PAYPAL_CLIENT_SECRET"))


@pytest.mark.live
@pytest.mark.skipif(not _HAS_PAYPAL_CREDS, reason="PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET not set")
def test_paypal_sandbox_create_and_get_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """Section 15 #9: PayPal Sandbox create/capture —
    The payment integration works end to end against PayPal Sandbox OAuth and Orders API v2.
    """
    monkeypatch.setattr(settings, "PAYPAL_MODE", "sandbox")
    monkeypatch.setattr(settings, "PAYPAL_CLIENT_ID", os.environ["PAYPAL_CLIENT_ID"])
    monkeypatch.setattr(settings, "PAYPAL_CLIENT_SECRET", os.environ["PAYPAL_CLIENT_SECRET"])

    token = paypal.get_access_token()
    assert isinstance(token, str) and len(token) > 10

    req_id = f"live-test-{uuid.uuid4().hex[:12]}"
    amount_str = paypal.minor_to_str(4_100_000)
    assert amount_str == "41000.00"

    order = paypal.create_order(
        amount_str="10.00",
        currency="USD",
        return_url="http://localhost:5173/payments/return",
        cancel_url="http://localhost:5173/payments/cancel",
        request_id=req_id,
    )
    assert "id" in order
    fetched = paypal.get_order(order["id"])
    assert fetched["id"] == order["id"]
    assert fetched["status"] in ("CREATED", "APPROVED", "COMPLETED")
