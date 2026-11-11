"""Plans router: GET /plans/{id}, POST /plans/{id}/payguard, POST /plans/{id}/approve, POST /plans/{id}/pay."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.enums import ErrorCode, PlanStatus, Verdict
from app.errors import ApiError
from app.models import Plan
from app.payments import service as payment_service
from app.schemas import (
    ApproveRequest,
    PayGuardResult,
    PayRequest,
    PayResponse,
    PlanOut,
)

router = APIRouter(tags=["plans"])

DbSession = Annotated[Session, Depends(get_db)]
OptionalApproveBody = Annotated[ApproveRequest | None, Body()]
OptionalPayBody = Annotated[PayRequest | None, Body()]


@router.get("/plans/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: int, db: DbSession) -> PlanOut:
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Plan {plan_id} not found")
    return payment_service.plan_to_out(db, plan)


@router.post("/plans/{plan_id}/payguard", response_model=PayGuardResult)
def rerun_payguard(plan_id: int, db: DbSession) -> PayGuardResult:
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Plan {plan_id} not found")

    if plan.status in (PlanStatus.PAYING, PlanStatus.PAID):
        raise ApiError(
            ErrorCode.CONFLICT,
            f"Cannot re-run PayGuard when plan status is {plan.status}",
        )

    pg = payment_service._run_for_plan(db, plan.id)
    plan.payguard_result = pg.model_dump(mode="json")

    if plan.status in (PlanStatus.DRAFT, PlanStatus.CHECKED):
        plan.status = PlanStatus.CHECKED
    elif plan.status == PlanStatus.USER_APPROVED:
        ack_set = set(plan.acknowledged_flags or [])
        unacked = [f.id for f in pg.flags if f.requires_ack and f.id not in ack_set]
        if pg.verdict == Verdict.BLOCKED or unacked:
            plan.status = PlanStatus.CHECKED

    db.commit()
    return pg


@router.post("/plans/{plan_id}/approve", response_model=PlanOut)
def approve_plan(
    plan_id: int,
    db: DbSession,
    body: OptionalApproveBody = None,
) -> PlanOut:
    req = body or ApproveRequest()
    return payment_service.approve(db, plan_id, req.acknowledged_flags)


@router.post("/plans/{plan_id}/pay", response_model=PayResponse)
def pay_plan(
    plan_id: int,
    db: DbSession,
    _body: OptionalPayBody = None,
) -> PayResponse:
    return payment_service.pay(db, plan_id)
