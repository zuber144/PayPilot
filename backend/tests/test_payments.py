"""Tests for payment idempotency, untrusted client inputs, and server-side plan verification."""

import pytest
from fastapi.testclient import TestClient

from app.enums import ErrorCode, PlanStatus, TxnStatus
from app.payments import paypal


def _create_clean_plan(client: TestClient) -> dict:
    resp = client.post(
        "/api/v1/goals",
        json={
            "raw_text": "Corporate event in Bangalore: catering for 100 people and a photographer",
            "budget_minor": 5_000_000,
            "currency": "INR",
            "scenario": "clean",
        },
    )
    assert resp.status_code in (200, 201, 202)
    goal_id = resp.json()["id"]
    goal = client.get(f"/api/v1/goals/{goal_id}").json()
    assert goal["plan_id"] is not None
    plan = client.get(f"/api/v1/plans/{goal['plan_id']}").json()
    return plan


def test_duplicate_pay_reuses_order_and_calls_paypal_once(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Section 15 #7: Duplicate payment request —
    Idempotency prevents duplicate live orders (duplicate /pay reuses the same order and PayPal create is called once).
    """
    plan = _create_clean_plan(client)
    plan_id = plan["id"]

    approve_resp = client.post(f"/api/v1/plans/{plan_id}/approve", json={"acknowledged_flags": []})
    assert approve_resp.status_code == 200

    create_calls: list[tuple[str, str, str]] = []
    orig_create = paypal.create_order

    def spy_create_order(
        amount_str: str, currency: str, return_url: str, cancel_url: str, request_id: str
    ) -> dict:
        create_calls.append((amount_str, currency, request_id))
        return orig_create(amount_str, currency, return_url, cancel_url, request_id)

    monkeypatch.setattr(paypal, "create_order", spy_create_order)

    pay1 = client.post(f"/api/v1/plans/{plan_id}/pay", json={})
    assert pay1.status_code == 200
    body1 = pay1.json()
    assert body1["reused"] is False

    pay2 = client.post(f"/api/v1/plans/{plan_id}/pay", json={})
    assert pay2.status_code == 200
    body2 = pay2.json()
    assert body2["paypal_order_id"] == body1["paypal_order_id"]
    assert body2["approval_url"] == body1["approval_url"]
    assert body2["reused"] is True
    assert len(create_calls) == 1


def test_client_altered_amount_or_verdict_is_ignored(client: TestClient) -> None:
    """Section 15 #10: Frontend sends altered amount/verdict —
    Backend ignores untrusted client payment values and charges the stored plan total.
    """
    plan = _create_clean_plan(client)
    plan_id = plan["id"]
    stored_total = plan["total_minor"]
    assert stored_total > 100

    # Send tampered fields in /approve
    approve_resp = client.post(
        f"/api/v1/plans/{plan_id}/approve",
        json={
            "acknowledged_flags": [],
            "total_minor": 100,
            "amount_minor": 100,
            "verdict": "APPROVED",
        },
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["total_minor"] == stored_total

    # Send tampered fields in /pay
    pay_resp = client.post(
        f"/api/v1/plans/{plan_id}/pay",
        json={
            "amount_minor": 100,
            "total_minor": 100,
            "currency": "USD",
            "verdict": "APPROVED",
        },
    )
    assert pay_resp.status_code == 200
    order_id = pay_resp.json()["paypal_order_id"]

    # Capture and verify charged amount equals stored plan total
    cap_resp = client.post(
        "/api/v1/payments/capture",
        json={"paypal_order_id": order_id, "amount_minor": 100},
    )
    assert cap_resp.status_code == 200
    txn = cap_resp.json()
    assert txn["amount_minor"] == stored_total
    assert txn["status"] == TxnStatus.COMPLETED


def test_pay_rejects_unapproved_plan(client: TestClient) -> None:
    """Work-division 3.9: Calling /pay before /approve is rejected with PLAN_NOT_APPROVED."""
    plan = _create_clean_plan(client)
    assert plan["status"] == PlanStatus.CHECKED

    pay_resp = client.post(f"/api/v1/plans/{plan['id']}/pay", json={})
    assert pay_resp.status_code == 409
    err = pay_resp.json()
    assert err["error"]["code"] == ErrorCode.PLAN_NOT_APPROVED
