"""
app/routers/plans.py — plan management, PayGuard, approve, and pay endpoints.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Goal, Plan
from app.payguard.engine import run_payguard
from app.payments.service import initiate_pay
from app.schemas import ApproveRequest, PayGuardResult, PayResponse, PlanOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/plans", tags=["plans"])


def _get_plan_or_404(plan_id: int, db: Session) -> Plan:
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    return plan


def _api_err(status: int, code: str, msg: str, details: Any = None) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": msg, "details": details}},
    )


@router.get("/{plan_id}")
def get_plan(plan_id: int, db: Session = Depends(get_db)) -> PlanOut:
    plan = _get_plan_or_404(plan_id, db)
    return PlanOut.model_validate(plan)


@router.post("/{plan_id}/payguard")
def run_payguard_check(plan_id: int, db: Session = Depends(get_db)) -> PayGuardResult:
    plan = _get_plan_or_404(plan_id, db)
    goal = db.get(Goal, plan.goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    if plan.status not in ("DRAFT", "CHECKED"):
        raise _api_err(409, "WRONG_STATE", f"PayGuard can only run on DRAFT/CHECKED plans, got {plan.status}")

    result = run_payguard(
        plan_id=plan.id,
        items=list(plan.items),
        plan_total=plan.total_minor,
        plan_currency=plan.currency,
        budget_minor=goal.budget_minor,
        goal_text=goal.raw_text,
        db=db,
    )

    plan.payguard_result = result.model_dump()
    if result.verdict == "BLOCKED":
        plan.status = "BLOCKED"
    else:
        plan.status = "CHECKED"
    db.commit()

    return result


@router.post("/{plan_id}/approve")
def approve_plan(
    plan_id: int,
    body: ApproveRequest,
    db: Session = Depends(get_db),
) -> PlanOut:
    plan = _get_plan_or_404(plan_id, db)

    if plan.status == "BLOCKED":
        raise _api_err(409, "PLAN_BLOCKED", "Cannot approve a BLOCKED plan")

    if plan.status not in ("CHECKED",):
        raise _api_err(
            409,
            "WRONG_STATE",
            f"Plan must be CHECKED to approve, got {plan.status}",
        )

    payguard = plan.payguard_result or {}
    flags = payguard.get("flags", [])
    verdict = payguard.get("verdict", "")

    if verdict == "REVIEW" and flags:
        missing = [f for f in flags if f not in body.acknowledged_flags]
        if missing:
            raise _api_err(
                409,
                "FLAGS_NOT_ACKNOWLEDGED",
                "All REVIEW flags must be acknowledged before approval",
                {"missing_flags": missing},
            )

    plan.status = "APPROVED"
    plan.approved_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    db.refresh(plan)
    return PlanOut.model_validate(plan)


@router.post("/{plan_id}/pay")
def pay_plan(plan_id: int, db: Session = Depends(get_db)) -> PayResponse:
    return initiate_pay(plan_id, db)
