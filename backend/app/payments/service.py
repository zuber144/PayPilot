"""Payment business logic: approve, pay, capture, reconcile, and schema serialization helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import ErrorCode, PlanStatus, TxnStatus, Verdict
from app.errors import ApiError
from app.models import Goal, Plan, Transaction
from app.payments import paypal
from app.payments.paypal import PayPalError
from app.schemas import PayGuardResult, PayResponse, PlanItem, PlanOut, TransactionOut


def _run_for_plan(db: Session, plan_id: int) -> PayGuardResult:
    from app.payguard import engine as pg_engine

    return pg_engine.run_for_plan(db, plan_id)


def plan_to_out(db: Session, plan: Plan) -> PlanOut:
    goal = db.get(Goal, plan.goal_id)
    budget_minor = goal.budget_minor if goal is not None else 0
    items = [PlanItem.model_validate(item) for item in (plan.items or [])]
    pg = PayGuardResult.model_validate(plan.payguard_result) if plan.payguard_result else None
    return PlanOut(
        id=plan.id,
        goal_id=plan.goal_id,
        status=PlanStatus(plan.status),
        currency=plan.currency,
        total_minor=plan.total_minor,
        budget_minor=budget_minor,
        rationale=plan.rationale or "",
        items=items,
        payguard=pg,
        acknowledged_flags=list(plan.acknowledged_flags or []),
        approved_at=plan.approved_at,
    )


def transaction_to_out(db: Session, txn: Transaction) -> TransactionOut:
    plan = db.get(Plan, txn.plan_id)
    goal_id: int | None = None
    goal_summary: str | None = None
    if plan is not None:
        goal_id = plan.goal_id
        goal = db.get(Goal, plan.goal_id)
        if goal is not None:
            goal_summary = goal.raw_text[:80]
    return TransactionOut(
        id=txn.id,
        plan_id=txn.plan_id,
        goal_id=goal_id,
        goal_summary=goal_summary,
        paypal_order_id=txn.paypal_order_id,
        capture_id=txn.capture_id,
        amount_minor=txn.amount_minor,
        currency=txn.currency,
        status=TxnStatus(txn.status),
        created_at=txn.created_at,
    )


def _extract_approval_url(order_data: dict[str, Any], order_id: str) -> str:
    links = order_data.get("links")
    if isinstance(links, list):
        for link in links:
            if isinstance(link, dict) and link.get("rel") in ("approve", "payer-action"):
                href = link.get("href")
                if isinstance(href, str) and href:
                    return href
    return f"{settings.FRONTEND_URL.rstrip('/')}/payments/return?token={order_id}"


def _extract_capture_details(order_data: dict[str, Any], order_id: str) -> tuple[str, int | None, str | None]:
    """Return (capture_id, captured_amount_minor, captured_currency)."""
    capture_id: str | None = None
    amt_minor: int | None = None
    currency: str | None = None

    units = order_data.get("purchase_units")
    if isinstance(units, list) and units:
        u0 = units[0]
        if isinstance(u0, dict):
            payments = u0.get("payments")
            if isinstance(payments, dict):
                captures = payments.get("captures")
                if isinstance(captures, list) and captures:
                    c0 = captures[0]
                    if isinstance(c0, dict):
                        cid = c0.get("id")
                        if isinstance(cid, str) and cid:
                            capture_id = cid
                        amt_obj = c0.get("amount")
                        if isinstance(amt_obj, dict):
                            val = amt_obj.get("value")
                            curr = amt_obj.get("currency_code")
                            if isinstance(val, str):
                                amt_minor = paypal.str_to_minor(val)
                            if isinstance(curr, str):
                                currency = curr
            if amt_minor is None:
                amt_obj = u0.get("amount")
                if isinstance(amt_obj, dict):
                    val = amt_obj.get("value")
                    curr = amt_obj.get("currency_code")
                    if isinstance(val, str):
                        amt_minor = paypal.str_to_minor(val)
                    if isinstance(curr, str):
                        currency = curr

    if not capture_id:
        top_cid = order_data.get("capture_id")
        if isinstance(top_cid, str) and top_cid:
            capture_id = top_cid
        else:
            capture_id = f"CAP-{order_id}"

    return capture_id, amt_minor, currency


def approve(db: Session, plan_id: int, acknowledged: list[str]) -> PlanOut:
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Plan {plan_id} not found")

    if plan.status not in (PlanStatus.CHECKED, PlanStatus.USER_APPROVED):
        raise ApiError(
            ErrorCode.PLAN_NOT_APPROVED,
            f"Plan cannot be approved from status {plan.status}",
        )

    if not plan.payguard_result:
        raise ApiError(ErrorCode.PLAN_NOT_APPROVED, "Plan has not been evaluated by PayGuard")

    pg = PayGuardResult.model_validate(plan.payguard_result)
    if pg.verdict == Verdict.BLOCKED:
        raise ApiError(ErrorCode.PLAN_NOT_APPROVED, "Plan is BLOCKED by PayGuard")

    ack_set = set(acknowledged or [])
    missing = [f.id for f in pg.flags if f.requires_ack and f.id not in ack_set]
    if missing:
        raise ApiError(
            ErrorCode.VALIDATION_ERROR,
            f"Missing required flag acknowledgements: {', '.join(missing)}",
        )

    plan.acknowledged_flags = list(acknowledged or [])
    if plan.approved_at is None or plan.status != PlanStatus.USER_APPROVED:
        plan.approved_at = datetime.now(UTC)
    plan.status = PlanStatus.USER_APPROVED
    db.commit()
    db.refresh(plan)
    return plan_to_out(db, plan)


def pay(db: Session, plan_id: int) -> PayResponse:
    if not settings.PAYMENTS_ENABLED:
        raise ApiError(ErrorCode.PAYMENTS_DISABLED, "Payments are currently disabled")

    plan = db.get(Plan, plan_id)
    if plan is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Plan {plan_id} not found")

    if plan.status == PlanStatus.PAID:
        raise ApiError(ErrorCode.DUPLICATE_PAYMENT, f"Plan {plan_id} is already PAID")

    if plan.status == PlanStatus.PAYING:
        existing_txn = db.scalars(
            select(Transaction)
            .where(Transaction.plan_id == plan.id, Transaction.status == TxnStatus.CREATED)
            .order_by(Transaction.id.desc())
        ).first()
        if existing_txn is not None:
            return PayResponse(
                plan_id=plan.id,
                paypal_order_id=existing_txn.paypal_order_id,
                approval_url=existing_txn.approval_url,
                status=PlanStatus(plan.status),
                reused=True,
            )

    if plan.status != PlanStatus.USER_APPROVED:
        raise ApiError(
            ErrorCode.PLAN_NOT_APPROVED,
            f"Plan {plan_id} must be USER_APPROVED before payment (current: {plan.status})",
        )

    pg = _run_for_plan(db, plan.id)
    plan.payguard_result = pg.model_dump(mode="json")

    if pg.verdict == Verdict.BLOCKED:
        plan.status = PlanStatus.CHECKED
        db.commit()
        raise ApiError(ErrorCode.PLAN_NOT_APPROVED, "Plan is BLOCKED by PayGuard")

    ack_set = set(plan.acknowledged_flags or [])
    unacked = [f.id for f in pg.flags if f.requires_ack and f.id not in ack_set]
    if pg.verdict == Verdict.REVIEW and unacked:
        plan.status = PlanStatus.CHECKED
        db.commit()
        raise ApiError(
            ErrorCode.PLAN_NOT_APPROVED,
            f"Plan requires acknowledgement for flags: {', '.join(unacked)}",
        )

    amount_str = paypal.minor_to_str(plan.total_minor)
    request_id = f"plan-{plan.id}"
    base_front = settings.FRONTEND_URL.rstrip("/")
    return_url = f"{base_front}/payments/return"
    cancel_url = f"{base_front}/plans/{plan.id}"

    try:
        order_data = paypal.create_order(
            amount_str=amount_str,
            currency=plan.currency,
            return_url=return_url,
            cancel_url=cancel_url,
            request_id=request_id,
        )
    except PayPalError as exc:
        db.commit()
        raise ApiError(ErrorCode.PAYPAL_ERROR, str(exc)) from exc

    order_id = str(order_data["id"])
    approval_url = _extract_approval_url(order_data, order_id)

    txn = Transaction(
        plan_id=plan.id,
        paypal_order_id=order_id,
        request_id=request_id,
        approval_url=approval_url,
        amount_minor=plan.total_minor,
        currency=plan.currency,
        status=TxnStatus.CREATED,
        raw=order_data,
    )
    db.add(txn)
    plan.status = PlanStatus.PAYING
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalars(
            select(Transaction).where(
                (Transaction.request_id == request_id) | (Transaction.paypal_order_id == order_id)
            )
        ).first()
        if existing is not None:
            plan_ref = db.get(Plan, plan.id)
            st = PlanStatus(plan_ref.status) if plan_ref else PlanStatus.PAYING
            return PayResponse(
                plan_id=plan.id,
                paypal_order_id=existing.paypal_order_id,
                approval_url=existing.approval_url,
                status=st,
                reused=True,
            )
        raise ApiError(ErrorCode.CONFLICT, "Concurrent payment creation conflict") from None

    return PayResponse(
        plan_id=plan.id,
        paypal_order_id=order_id,
        approval_url=approval_url,
        status=PlanStatus.PAYING,
        reused=False,
    )


def _record_completed_capture(
    db: Session,
    txn: Transaction,
    plan: Plan,
    payload: dict[str, Any],
) -> TransactionOut:
    try:
        capture_id, captured_minor, captured_currency = _extract_capture_details(
            payload, txn.paypal_order_id
        )
    except PayPalError as exc:
        txn.status = TxnStatus.FAILED
        plan.status = PlanStatus.FAILED
        db.commit()
        raise ApiError(ErrorCode.PAYPAL_ERROR, str(exc)) from exc

    if captured_minor is not None and captured_minor != txn.amount_minor:
        txn.status = TxnStatus.FAILED
        plan.status = PlanStatus.FAILED
        db.commit()
        raise ApiError(
            ErrorCode.PAYPAL_ERROR,
            f"Captured amount {captured_minor} does not match expected {txn.amount_minor}",
        )

    if captured_currency is not None and captured_currency != txn.currency:
        txn.status = TxnStatus.FAILED
        plan.status = PlanStatus.FAILED
        db.commit()
        raise ApiError(
            ErrorCode.PAYPAL_ERROR,
            f"Captured currency {captured_currency} does not match expected {txn.currency}",
        )

    txn.capture_id = capture_id
    txn.raw = payload
    txn.status = TxnStatus.COMPLETED
    plan.status = PlanStatus.PAID
    db.commit()
    db.refresh(txn)
    return transaction_to_out(db, txn)


def capture(db: Session, order_id: str) -> TransactionOut:
    if not settings.PAYMENTS_ENABLED:
        raise ApiError(ErrorCode.PAYMENTS_DISABLED, "Payments are currently disabled")

    txn = db.scalars(
        select(Transaction).where(Transaction.paypal_order_id == order_id)
    ).first()
    if txn is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Transaction for order {order_id} not found")

    if txn.status == TxnStatus.COMPLETED:
        return transaction_to_out(db, txn)

    plan = db.get(Plan, txn.plan_id)
    if plan is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Plan {txn.plan_id} not found")

    if plan.status != PlanStatus.PAYING:
        raise ApiError(
            ErrorCode.PLAN_NOT_APPROVED,
            f"Plan {plan.id} is not in PAYING state (current: {plan.status})",
        )

    try:
        cap_data = paypal.capture_order(order_id, request_id=f"capture-{txn.request_id}")
    except PayPalError as exc:
        raise ApiError(ErrorCode.PAYPAL_ERROR, str(exc)) from exc

    if cap_data.get("status") != "COMPLETED":
        txn.status = TxnStatus.FAILED
        plan.status = PlanStatus.FAILED
        txn.raw = cap_data
        db.commit()
        raise ApiError(
            ErrorCode.PAYPAL_ERROR,
            f"PayPal capture did not complete (status: {cap_data.get('status')})",
        )

    return _record_completed_capture(db, txn, plan, cap_data)


def reconcile(db: Session, plan_id: int) -> TransactionOut | None:
    """Reconcile a missed browser return by checking order status with PayPal."""
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Plan {plan_id} not found")

    txn = db.scalars(
        select(Transaction)
        .where(Transaction.plan_id == plan.id)
        .order_by(Transaction.id.desc())
    ).first()
    if txn is None:
        return None

    if txn.status == TxnStatus.COMPLETED:
        return transaction_to_out(db, txn)

    try:
        order_data = paypal.get_order(txn.paypal_order_id)
    except PayPalError as exc:
        raise ApiError(ErrorCode.PAYPAL_ERROR, str(exc)) from exc

    order_status = order_data.get("status")
    if order_status == "APPROVED":
        return capture(db, txn.paypal_order_id)
    if order_status == "COMPLETED":
        return _record_completed_capture(db, txn, plan, order_data)

    return transaction_to_out(db, txn)
