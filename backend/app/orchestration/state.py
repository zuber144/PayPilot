"""Shared LangGraph state (`AgentState`) and trace event helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, TypedDict

from app.enums import GoalStatus, TraceNode, TraceStatus
from app.schemas import (
    CoverageReport,
    Filters,
    Need,
    OfferDraft,
    PayGuardResult,
    PlanDraft,
    ProviderOut,
    TraceEvent,
)


class AgentState(TypedDict, total=False):
    goal_id: int
    raw_text: str
    budget_minor: int
    currency: str
    scenario: str | None
    needs: list[Need]
    deadline_days: int | None
    question: str | None
    filters: dict[str, Any]
    last_relaxed: list[str]
    include_unverified: bool
    candidates: dict[str, list[ProviderOut]]
    coverage: CoverageReport | None
    offers: list[OfferDraft]
    all_offers: list[OfferDraft]
    providers_by_id: dict[int, ProviderOut]
    plan: PlanDraft | None
    plan_id: int | None
    payguard: PayGuardResult | None
    retries: dict[str, int]
    stage: str
    planning_attempted: bool
    steps: int
    trace: list[TraceEvent]
    status: str
    next_action: str | None


def make_initial_state(
    *,
    goal_id: int,
    raw_text: str,
    budget_minor: int,
    currency: str = "INR",
    scenario: str | None = None,
    filters: Filters | dict[str, Any] | None = None,
    include_unverified: bool = False,
) -> AgentState:
    filter_dict: dict[str, Any]
    if isinstance(filters, Filters):
        filter_dict = filters.model_dump()
    elif isinstance(filters, dict):
        filter_dict = dict(filters)
    else:
        filter_dict = Filters().model_dump()

    return AgentState(
        goal_id=goal_id,
        raw_text=raw_text,
        budget_minor=budget_minor,
        currency=currency,
        scenario=scenario,
        needs=[],
        deadline_days=None,
        question=None,
        filters=filter_dict,
        last_relaxed=[],
        include_unverified=include_unverified,
        candidates={},
        coverage=None,
        offers=[],
        all_offers=[],
        providers_by_id={},
        plan=None,
        plan_id=None,
        payguard=None,
        retries={"discovery": 0, "negotiation": 0, "plan_revision": 0},
        stage="init",
        planning_attempted=False,
        steps=0,
        trace=[],
        status=GoalStatus.RUNNING.value,
        next_action=None,
    )


def get_filters(state: AgentState) -> Filters:
    raw = state.get("filters")
    if isinstance(raw, Filters):
        return raw
    if isinstance(raw, dict):
        return Filters.model_validate(raw)
    return Filters()


def append_trace(
    state: AgentState,
    *,
    node: TraceNode,
    action: str,
    status: TraceStatus,
    summary: str,
    reason: str = "",
    duration_ms: int = 0,
    data: dict[str, Any] | None = None,
) -> TraceEvent:
    trace_list = list(state.get("trace", []))
    event = TraceEvent(
        seq=len(trace_list) + 1,
        ts=datetime.now(UTC),
        node=node,
        action=action,
        status=status,
        summary=summary,
        reason=reason,
        duration_ms=max(0, int(duration_ms)),
        data=dict(data) if data else {},
    )
    trace_list.append(event)
    state["trace"] = trace_list
    return event
