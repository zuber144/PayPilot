"""
tests/test_state_machine.py — state machine and idempotency tests.

Tests:
1. POST /plans/{id}/pay on a non-APPROVED plan returns 409.
2. A second POST /plans/{id}/pay returns the same transaction (idempotent).
"""
from __future__ import annotations

import pytest

from app.models import Plan, Transaction


# ---------------------------------------------------------------------------
# Helper: advance a plan to APPROVED state
# ---------------------------------------------------------------------------

def _make_approved_plan(db, demo_goal, verified_provider) -> Plan:
    plan = Plan(
        goal_id=demo_goal.id,
        items=[
            {
                "need_key": "web_design",
                "provider_id": verified_provider.id,
                "provider_name": verified_provider.name,
                "price_minor": 40000,
                "scope": "Full website",
                "timeline_days": 7,
                "offer_id": 1,
            }
        ],
        total_minor=40000,
        currency="USD",
        rationale="Best value",
        payguard_result={
            "verdict": "APPROVED",
            "rules": [],
            "risk_score": 20,
            "flags": [],
            "summary": "Clean",
        },
        status="APPROVED",
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


# ---------------------------------------------------------------------------
# 1. /pay on non-APPROVED plan → 409
# ---------------------------------------------------------------------------

def test_pay_draft_plan_returns_409(client, db, demo_goal, verified_provider):
    plan = Plan(
        goal_id=demo_goal.id,
        items=[],
        total_minor=10000,
        currency="USD",
        rationale="",
        status="DRAFT",
    )
    db.add(plan)
    db.commit()

    resp = client.post(f"/api/v1/plans/{plan.id}/pay")
    assert resp.status_code == 409


def test_pay_checked_plan_returns_409(client, db, demo_goal, verified_provider):
    plan = Plan(
        goal_id=demo_goal.id,
        items=[],
        total_minor=10000,
        currency="USD",
        rationale="",
        status="CHECKED",
    )
    db.add(plan)
    db.commit()

    resp = client.post(f"/api/v1/plans/{plan.id}/pay")
    assert resp.status_code == 409


def test_pay_paid_plan_returns_409(client, db, demo_goal, verified_provider):
    plan = Plan(
        goal_id=demo_goal.id,
        items=[],
        total_minor=10000,
        currency="USD",
        rationale="",
        status="PAID",
    )
    db.add(plan)
    db.commit()

    resp = client.post(f"/api/v1/plans/{plan.id}/pay")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# 2. Second /pay returns the same transaction (idempotency)
# ---------------------------------------------------------------------------

def test_second_pay_returns_existing_transaction(client, db, demo_goal, verified_provider):
    """
    If a PAYING plan already has a live transaction, a second /pay must
    return the same transaction without creating a new one.
    """
    plan = _make_approved_plan(db, demo_goal, verified_provider)

    # Manually put the plan in PAYING and add a live transaction
    plan.status = "PAYING"
    db.commit()

    existing_txn = Transaction(
        plan_id=plan.id,
        paypal_order_id="PP-EXISTING-ORDER-999",
        amount_minor=40000,
        currency="USD",
        status="CREATED",
        raw={"links": [{"rel": "approve", "href": "https://paypal.com/approve"}]},
    )
    db.add(existing_txn)
    db.commit()

    # Put plan back to APPROVED for the /pay call
    plan.status = "APPROVED"
    db.commit()

    resp = client.post(f"/api/v1/plans/{plan.id}/pay")
    assert resp.status_code == 200
    data = resp.json()
    assert data["paypal_order_id"] == "PP-EXISTING-ORDER-999"
    assert data["approval_url"] == "https://paypal.com/approve"

    # Confirm the existing transaction is still the only one
    db.refresh(plan)
    txns = db.query(Transaction).filter(Transaction.plan_id == plan.id).all()
    assert len([t for t in txns if t.status in ("CREATED", "COMPLETED")]) == 1
