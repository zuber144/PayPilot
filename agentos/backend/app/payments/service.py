"""
app/payments/service.py — plan state machine + PayPal order creation (FULLY IMPLEMENTED).

State machine (forward only):
  DRAFT → CHECKED → APPROVED → PAYING → PAID
  with BLOCKED and PAY_FAILED as side exits.

Key functions:
  initiate_pay(plan_id, db) — idempotent; returns existing live transaction or creates one.
  capture_payment(paypal_order_id, db) — captures the order and transitions to PAID.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Plan, Transaction
from app.payments.paypal import capture_order, create_order
from app.payguard.engine import run_payguard
from app.schemas import CaptureResponse, PayResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid state transitions
# ---------------------------------------------------------------------------

_TRANSITIONS: dict[str, str] = {
    "DRAFT": "CHECKED",
    "CHECKED": "APPROVED",
    "APPROVED": "PAYING",
    "PAYING": "PAID",
}

_TERMINAL_STATES = {"PAID", "BLOCKED", "PAY_FAILED"}


def _get_plan_or_404(plan_id: int, db: Session) -> Plan:
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    return plan


def _api_error(status_code: int, code: str, message: str, details: Any = None) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": details}},
    )


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def transition_plan(plan: Plan, to_status: str, db: Session) -> None:
    """Advance a plan to `to_status`. Commits the change."""
    plan.status = to_status
    db.commit()
    db.refresh(plan)


def get_live_transaction(plan_id: int, db: Session) -> Transaction | None:
    """Return an existing CREATED or COMPLETED transaction for this plan, if any."""
    return (
        db.query(Transaction)
        .filter(
            Transaction.plan_id == plan_id,
            Transaction.status.in_(["CREATED", "COMPLETED"]),
        )
        .first()
    )


# ---------------------------------------------------------------------------
# Public service operations
# ---------------------------------------------------------------------------

def initiate_pay(plan_id: int, db: Session) -> PayResponse:
    """
    Idempotent /pay operation:
    1. Validates the plan is APPROVED.
    2. Re-runs the full PayGuard policy check.
    3. Returns the existing live transaction if one exists (idempotency).
    4. Otherwise creates a PayPal order and a Transaction record.
    """
    plan = _get_plan_or_404(plan_id, db)
    goal = plan.goal

    # Only APPROVED plans may proceed to payment
    if plan.status != "APPROVED":
        raise _api_error(
            409,
            "PLAN_NOT_APPROVED",
            f"Plan is in state '{plan.status}', must be APPROVED to pay",
        )

    # Idempotency: return existing live transaction
    existing = get_live_transaction(plan_id, db)
    if existing:
        # Find approval URL in raw response
        approval_url = _extract_approval_url(existing.raw or {})
        return PayResponse(
            transaction_id=existing.id,
            paypal_order_id=existing.paypal_order_id,
            approval_url=approval_url,
            status=existing.status,
        )

    # Re-run policy layer before creating order
    payguard = run_payguard(
        plan_id=plan.id,
        items=list(plan.items),
        plan_total=plan.total_minor,
        plan_currency=plan.currency,
        budget_minor=goal.budget_minor,
        goal_text=goal.raw_text,
        db=db,
    )

    if payguard.verdict == "BLOCKED":
        plan.status = "BLOCKED"
        plan.payguard_result = payguard.model_dump()
        db.commit()
        raise _api_error(
            409,
            "PLAN_BLOCKED",
            "PayGuard blocked this payment",
            payguard.model_dump(),
        )

    # Transition plan to PAYING
    plan.status = "PAYING"
    db.commit()

    # Create PayPal order
    # We need a transaction ID for the PayPal-Request-Id header; create the record first
    txn = Transaction(
        plan_id=plan_id,
        paypal_order_id="PENDING",  # filled in after PayPal responds
        amount_minor=plan.total_minor,
        currency=plan.currency,
        status="CREATED",
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    try:
        order_data = create_order(
            plan_id=plan_id,
            transaction_id=txn.id,
            amount_minor=plan.total_minor,
            currency=plan.currency,
        )
    except Exception as exc:
        logger.error("PayPal create_order failed: %s", exc)
        plan.status = "PAY_FAILED"
        txn.status = "FAILED"
        txn.raw = {"error": str(exc)}
        db.commit()
        raise _api_error(424, "PAYPAL_ERROR", "PayPal order creation failed", str(exc))

    paypal_order_id = order_data.get("id", "")
    txn.paypal_order_id = paypal_order_id
    txn.raw = order_data
    db.commit()

    approval_url = _extract_approval_url(order_data)
    return PayResponse(
        transaction_id=txn.id,
        paypal_order_id=paypal_order_id,
        approval_url=approval_url,
        status="CREATED",
    )


def capture_payment(paypal_order_id: str, db: Session) -> CaptureResponse:
    """
    Capture a PayPal order that has been approved by the buyer.
    Transitions plan to PAID and stores the capture data.
    """
    txn = db.query(Transaction).filter(
        Transaction.paypal_order_id == paypal_order_id
    ).first()
    if not txn:
        raise _api_error(404, "TRANSACTION_NOT_FOUND", f"No transaction for order {paypal_order_id}")

    plan = _get_plan_or_404(txn.plan_id, db)

    if plan.status != "PAYING":
        raise _api_error(
            409,
            "PLAN_NOT_PAYING",
            f"Plan status is '{plan.status}', expected PAYING for capture",
        )

    try:
        capture_data = capture_order(paypal_order_id)
    except Exception as exc:
        logger.error("PayPal capture failed: %s", exc)
        plan.status = "PAY_FAILED"
        txn.status = "FAILED"
        db.commit()
        raise _api_error(424, "PAYPAL_CAPTURE_ERROR", "PayPal capture failed", str(exc))

    capture_id = _extract_capture_id(capture_data)
    txn.capture_id = capture_id
    txn.status = "COMPLETED"
    txn.raw = capture_data
    plan.status = "PAID"
    db.commit()

    return CaptureResponse(
        transaction_id=txn.id,
        capture_id=capture_id or "",
        amount_minor=txn.amount_minor,
        currency=txn.currency,
        status="COMPLETED",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_approval_url(order_data: dict) -> str:
    """Find the payer-approval link in a PayPal order response."""
    for link in order_data.get("links", []):
        if link.get("rel") in ("approve", "payer-action"):
            return str(link.get("href", ""))
    return ""


def _extract_capture_id(capture_data: dict) -> str | None:
    """Extract the capture ID from a PayPal capture response."""
    for unit in capture_data.get("purchase_units", []):
        for capture in unit.get("payments", {}).get("captures", []):
            return str(capture.get("id", ""))
    return None
