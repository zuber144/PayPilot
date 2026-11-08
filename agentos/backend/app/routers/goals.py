"""
app/routers/goals.py — goal creation and status polling.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.pipeline import PipelineRunner
from app.db import get_db
from app.models import Goal, Offer, Plan
from app.schemas import GoalCreate, GoalOut, OfferOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/goals", tags=["goals"])


def _goal_to_out(goal: Goal, db: Session) -> GoalOut:
    plan = db.query(Plan).filter(Plan.goal_id == goal.id).first()
    return GoalOut(
        id=goal.id,
        user_id=goal.user_id,
        raw_text=goal.raw_text,
        parsed=goal.parsed,
        budget_minor=goal.budget_minor,
        currency=goal.currency,
        status=goal.status,
        trace=list(goal.trace or []),
        created_at=goal.created_at,
        plan_id=plan.id if plan else None,
    )


def _run_pipeline(goal_id: int, db: Session) -> None:
    """Background task wrapper for PipelineRunner."""
    try:
        runner = PipelineRunner(db)
        runner.run(goal_id)
    except Exception as exc:
        logger.exception("Background pipeline error for goal %d: %s", goal_id, exc)
    finally:
        db.close()


@router.post("", status_code=202)
def create_goal(
    body: GoalCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> GoalOut:
    goal = Goal(
        user_id=body.user_id,
        raw_text=body.raw_text,
        budget_minor=body.budget_minor,
        currency=body.currency,
        status="NEW",
        trace=[],
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)

    # Spin up pipeline in a background task
    background_tasks.add_task(_run_pipeline, goal.id, db)
    logger.info("Goal %d created; pipeline queued", goal.id)
    return _goal_to_out(goal, db)


@router.get("/{goal_id}")
def get_goal(goal_id: int, db: Session = Depends(get_db)) -> GoalOut:
    goal = db.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
    return _goal_to_out(goal, db)


@router.get("/{goal_id}/offers")
def get_goal_offers(goal_id: int, db: Session = Depends(get_db)) -> list[OfferOut]:
    goal = db.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
    offers = db.query(Offer).filter(Offer.goal_id == goal_id).all()
    return [OfferOut.model_validate(o) for o in offers]
