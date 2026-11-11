"""Goals router: POST /goals, GET /goals/{id}, GET /goals/{id}/offers."""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.enums import ErrorCode, GoalStatus, OfferStatus, Scenario
from app.errors import ApiError
from app.models import Goal, Offer, Plan, Provider
from app.schemas import (
    GoalCreate,
    GoalCreated,
    GoalOut,
    OfferGroup,
    OfferRound,
    OffersOut,
    ParsedGoal,
    ProviderOffers,
    TraceEvent,
)

router = APIRouter(tags=["goals"])

DbSession = Annotated[Session, Depends(get_db)]


def _start_workflow(goal_id: int) -> None:
    from app.orchestration.graph import run_workflow

    run_workflow(goal_id)


@router.post("/goals", response_model=GoalCreated, status_code=status.HTTP_202_ACCEPTED)
def create_goal(
    body: GoalCreate,
    background_tasks: BackgroundTasks,
    db: DbSession,
) -> GoalCreated:
    goal = Goal(
        raw_text=body.raw_text,
        budget_minor=body.budget_minor,
        currency=body.currency,
        scenario=body.scenario.value if body.scenario else None,
        status=GoalStatus.RUNNING.value,
        trace=[],
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    background_tasks.add_task(_start_workflow, goal.id)
    return GoalCreated(id=goal.id, status=GoalStatus(goal.status))


@router.get("/goals/{goal_id}", response_model=GoalOut)
def get_goal(goal_id: int, db: DbSession) -> GoalOut:
    goal = db.get(Goal, goal_id)
    if goal is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Goal {goal_id} not found")

    latest_plan = db.scalars(
        select(Plan).where(Plan.goal_id == goal.id).order_by(Plan.id.desc())
    ).first()

    parsed = ParsedGoal.model_validate(goal.parsed) if goal.parsed else None
    trace = [TraceEvent.model_validate(ev) for ev in (goal.trace or [])]
    scenario = Scenario(goal.scenario) if goal.scenario else None

    return GoalOut(
        id=goal.id,
        status=GoalStatus(goal.status),
        raw_text=goal.raw_text,
        budget_minor=goal.budget_minor,
        currency=goal.currency,
        scenario=scenario,
        parsed=parsed,
        question=goal.question,
        trace=trace,
        plan_id=latest_plan.id if latest_plan else None,
        created_at=goal.created_at,
    )


@router.get("/goals/{goal_id}/offers", response_model=OffersOut)
def get_goal_offers(goal_id: int, db: DbSession) -> OffersOut:
    goal = db.get(Goal, goal_id)
    if goal is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Goal {goal_id} not found")

    offers = list(
        db.scalars(
            select(Offer)
            .where(Offer.goal_id == goal_id)
            .order_by(Offer.id.asc())
        ).all()
    )

    if not offers:
        return OffersOut(goal_id=goal_id, groups=[])

    provider_ids = {o.provider_id for o in offers}
    providers_by_id: dict[int, Provider] = {
        p.id: p
        for p in db.scalars(select(Provider).where(Provider.id.in_(provider_ids))).all()
    }

    need_order: list[str] = []
    if goal.parsed and isinstance(goal.parsed.get("needs"), list):
        for n in goal.parsed["needs"]:
            if isinstance(n, dict) and isinstance(n.get("key"), str):
                need_order.append(n["key"])

    by_need_and_provider: dict[str, dict[int, list[Offer]]] = defaultdict(lambda: defaultdict(list))
    for off in offers:
        if off.need_key not in need_order:
            need_order.append(off.need_key)
        by_need_and_provider[off.need_key][off.provider_id].append(off)

    groups: list[OfferGroup] = []
    for need_key in need_order:
        prov_map = by_need_and_provider.get(need_key)
        if not prov_map:
            continue
        provider_offers_list: list[ProviderOffers] = []
        for pid, p_offers in prov_map.items():
            p_offers_sorted = sorted(p_offers, key=lambda x: (x.round, x.id))
            first_off = p_offers_sorted[0]
            last_off = p_offers_sorted[-1]
            prov = providers_by_id.get(pid)
            rounds = [
                OfferRound(
                    round=r.round,
                    price_minor=r.price_minor,
                    counter_minor=r.counter_minor,
                    status=OfferStatus(r.status),
                    scope=r.scope or "",
                    packs=r.packs or 1,
                    shipping_minor=r.shipping_minor or 0,
                    tags=list(r.tags or []),
                )
                for r in p_offers_sorted
            ]
            provider_offers_list.append(
                ProviderOffers(
                    provider_id=pid,
                    provider_name=prov.name if prov else f"Provider {pid}",
                    verified=bool(prov.verified) if prov else False,
                    rating=float(prov.rating) if prov else 0.0,
                    timeline_days=last_off.timeline_days,
                    opening_price_minor=first_off.price_minor,
                    final_price_minor=last_off.price_minor,
                    status=OfferStatus(last_off.status),
                    rounds=rounds,
                    store=prov.store if prov else "",
                    product_title=prov.product_title if prov else "",
                    url=prov.url if prov else "",
                    pack_size=prov.pack_size if prov else 1,
                    review_count=prov.review_count if prov else 0,
                    tags=list(last_off.tags or []),
                    original_currency=prov.original_currency if prov else "INR",
                    original_price_minor=prov.original_price_minor if prov else 0,
                )
            )
        groups.append(OfferGroup(need_key=need_key, offers=provider_offers_list))

    return OffersOut(goal_id=goal_id, groups=groups)
