"""Tests for orchestration bounded loops, discovery retries, and router fallbacks."""

import pytest
from sqlalchemy.orm import Session

from app.config import settings
from app.enums import GoalStatus, Scenario, TraceNode, TraceStatus
from app.models import Goal, Provider
from app.orchestration import graph


def _create_goal(
    db: Session,
    raw_text: str = "Corporate event in Bangalore: catering for 100 people and a photographer",
    budget_minor: int = 5_000_000,
    currency: str = "USD",
    scenario: str | None = None,
) -> Goal:
    goal = Goal(
        raw_text=raw_text,
        budget_minor=budget_minor,
        currency=currency,
        scenario=scenario,
        status=GoalStatus.RUNNING,
        trace=[],
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def test_discovery_retry_when_coverage_insufficient(db: Session) -> None:
    """Section 15 #1: Discovery retry when provider coverage is insufficient —
    Orchestrator reacts to intermediate results and selects a conditional action.
    """
    goal = _create_goal(db, scenario=Scenario.RETRY)
    graph.run_workflow(goal.id)

    db.expire_all()
    updated = db.get(Goal, goal.id)
    assert updated is not None
    assert updated.status == GoalStatus.PLAN_READY

    retry_events = [
        ev
        for ev in updated.trace
        if ev.get("status") == TraceStatus.RETRY and ev.get("node") == TraceNode.ORCHESTRATOR
    ]
    assert len(retry_events) >= 1
    assert any("coverage" in (ev.get("reason", "") + " " + ev.get("summary", "")).lower() for ev in retry_events)


def test_max_discovery_retries_bounded(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Section 15 #2 (part 1): Maximum retry / iteration limit —
    The agentic loop is bounded and cannot run indefinitely (discovery retries <= MAX_DISCOVERY_RETRIES).
    """
    monkeypatch.setattr(settings, "MAX_DISCOVERY_RETRIES", 1)
    # Remove all verified photography providers so coverage is never sufficient
    db.query(Provider).filter(Provider.category == "photography").update({"verified": False})
    db.commit()

    goal = _create_goal(db, scenario=Scenario.RETRY)
    graph.run_workflow(goal.id)

    db.expire_all()
    updated = db.get(Goal, goal.id)
    assert updated is not None
    retry_events = [
        ev
        for ev in updated.trace
        if ev.get("status") == TraceStatus.RETRY and ev.get("action") == "retry_discovery"
    ]
    assert len(retry_events) <= 1
    assert updated.status in (GoalStatus.NEEDS_INPUT, GoalStatus.FAILED)


def test_max_graph_steps_hard_stop(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Section 15 #2 (part 2): Maximum retry / iteration limit —
    The agentic loop is bounded and stops at MAX_GRAPH_STEPS.
    """
    monkeypatch.setattr(settings, "MAX_GRAPH_STEPS", 2)
    goal = _create_goal(db, scenario=Scenario.CLEAN)
    graph.run_workflow(goal.id)

    db.expire_all()
    updated = db.get(Goal, goal.id)
    assert updated is not None
    assert updated.status != GoalStatus.RUNNING
    assert len(updated.trace) <= 6


def test_router_invalid_llm_output_falls_back(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Work-division 3.9: Invalid router output falls back to the default action with a FALLBACK trace event."""
    from app import llm

    orig_raw = llm._raw_completion

    def fake_raw(system: str, user: str, task: str) -> str:
        if task == "route":
            return '{"action": "unpermitted_nuclear_launch", "reason": "rogue"}'
        return orig_raw(system, user, task)

    monkeypatch.setattr(llm, "_raw_completion", fake_raw)

    goal = _create_goal(db, scenario=Scenario.CLEAN)
    graph.run_workflow(goal.id)

    db.expire_all()
    updated = db.get(Goal, goal.id)
    assert updated is not None
    assert updated.status == GoalStatus.PLAN_READY
    fallback_events = [
        ev
        for ev in updated.trace
        if ev.get("node") == TraceNode.ORCHESTRATOR and ev.get("status") == TraceStatus.FALLBACK
    ]
    assert len(fallback_events) >= 1


def test_negotiation_is_mandatory_before_planning() -> None:
    """With offers and no negotiation round yet, negotiate is the only allowed action."""
    from app.enums import Action
    from app.orchestration import router
    from app.schemas import Need, OfferDraft

    offer = OfferDraft(need_key="photography", provider_id=1, round=0, price_minor=1_800_000, timeline_days=4)
    base = {"needs": [Need(key="photography", category="photography")], "offers": [offer]}

    round0 = {**base, "retries": {"discovery": 0, "negotiation": 0, "plan_revision": 0}}
    assert router.allowed_actions(round0) == [Action.NEGOTIATE]  # type: ignore[arg-type]

    round1 = {**base, "retries": {"discovery": 0, "negotiation": 1, "plan_revision": 0}}
    assert router.allowed_actions(round1) == [Action.NEGOTIATE, Action.PLAN]  # type: ignore[arg-type]


def test_negotiation_disabled_by_config_goes_straight_to_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    """MAX_NEGOTIATION_ROUNDS=0 still bounds the loop: plan is the only action."""
    from app.enums import Action
    from app.orchestration import router
    from app.schemas import Need, OfferDraft

    monkeypatch.setattr(settings, "MAX_NEGOTIATION_ROUNDS", 0)
    offer = OfferDraft(need_key="photography", provider_id=1, round=0, price_minor=1_800_000, timeline_days=4)
    state = {
        "needs": [Need(key="photography", category="photography")],
        "offers": [offer],
        "retries": {"discovery": 0, "negotiation": 0, "plan_revision": 0},
    }
    assert router.allowed_actions(state) == [Action.PLAN]  # type: ignore[arg-type]


def test_router_llm_preferring_plan_still_negotiates_below_list_price(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: the live router LLM skipped negotiation and paid list price.

    A router that always picks 'plan' when allowed must still get at least one negotiation round,
    so the clean plan total lands below the providers' base (list) prices.
    """
    import json

    from app import llm
    from app.models import Plan

    orig_raw = llm._raw_completion
    allowed_seen: list[list[str]] = []

    def plan_happy_router(system: str, user: str, task: str) -> str:
        if task == "route":
            allowed = json.loads(user)["allowed"]
            allowed_seen.append(allowed)
            pick = "plan" if "plan" in allowed else allowed[0]
            return json.dumps({"action": pick, "reason": "prefer planning"})
        return orig_raw(system, user, task)

    monkeypatch.setattr(llm, "_raw_completion", plan_happy_router)

    goal = _create_goal(db, scenario=Scenario.CLEAN)
    graph.run_workflow(goal.id)

    db.expire_all()
    updated = db.get(Goal, goal.id)
    assert updated is not None
    assert updated.status == GoalStatus.PLAN_READY
    assert ["negotiate"] in allowed_seen, allowed_seen
    negotiation_events = [ev for ev in updated.trace if ev.get("node") == TraceNode.NEGOTIATION]
    assert len(negotiation_events) >= 1
    assert not [ev for ev in updated.trace if ev.get("status") == TraceStatus.FALLBACK]

    plan = db.query(Plan).filter(Plan.goal_id == goal.id).one()
    by_name = {p.name: p.base_price_minor for p in db.query(Provider).all()}
    list_total = sum(by_name[item["provider_name"]] for item in plan.items)
    assert plan.total_minor < list_total, (plan.total_minor, list_total)
