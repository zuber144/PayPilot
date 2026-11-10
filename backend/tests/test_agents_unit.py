"""Focused unit tests for goal_agent, discovery_agent, provider_agent, planning_agent, and seed."""

import sys
import types
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

# Provide a minimal fallback stub if Builder A's app.llm is not yet on disk during isolated testing
try:
    import app.llm as _llm_mod  # noqa: F401
except ModuleNotFoundError:
    _stub = types.ModuleType("app.llm")

    class _LLMFailure(Exception):
        pass

    def _call_json(system: str, user: str, schema_model: type[Any], *, task: str) -> Any:
        raise _LLMFailure("stub llm not patched")

    _stub.LLMFailure = _LLMFailure  # type: ignore[attr-defined]
    _stub.call_json = _call_json  # type: ignore[attr-defined]
    sys.modules["app.llm"] = _stub

from app.agents import (  # noqa: E402
    discovery_agent,
    goal_agent,
    negotiation_agent,
    planning_agent,
    provider_agent,
)
from app.llm import LLMFailure  # noqa: E402
from app.models import Provider, User  # noqa: E402
from app.schemas import (  # noqa: E402
    GoalLLMOut,
    Need,
    OfferTextLLMOut,
    ProviderOut,
    RationaleLLMOut,
)
from seed import seed  # noqa: E402


def test_seed_is_idempotent(db: Session) -> None:
    seed(db)
    seed(db)
    providers = db.execute(select(Provider)).scalars().all()
    users = db.execute(select(User)).scalars().all()
    assert len(providers) == 6
    assert len(users) == 1


def test_goal_agent_parses_unique_needs_and_defaults_currency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_call_json(system: str, user: str, schema_model: Any, *, task: str) -> GoalLLMOut:
        assert task == "goal_parse"
        return GoalLLMOut(
            needs=[
                Need(key="catering", category="catering", quantity=100),
                Need(key="catering", category="catering", quantity=50),  # duplicate key
                Need(key="photography", category="photography"),
            ],
            deadline_days=10,
            currency=None,
        )

    monkeypatch.setattr(goal_agent, "call_json", fake_call_json)
    res = goal_agent.run("Need catering for 100 people and photography", "INR")
    assert res.parsed is not None
    assert res.fallback is False
    assert res.question is None
    assert res.parsed.currency == "INR"
    assert [n.key for n in res.parsed.needs] == ["catering", "photography"]
    assert res.parsed.needs[0].quantity == 100


def test_goal_agent_empty_needs_sets_question(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_call_json(system: str, user: str, schema_model: Any, *, task: str) -> GoalLLMOut:
        return GoalLLMOut(needs=[], question="What services do you need?")

    monkeypatch.setattr(goal_agent, "call_json", fake_call_json)
    res = goal_agent.run("Help me plan something", "INR")
    assert res.parsed is None
    assert res.fallback is False
    assert res.question == "What services do you need?"


def test_goal_agent_llm_failure_sets_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_call_json(system: str, user: str, schema_model: Any, *, task: str) -> GoalLLMOut:
        raise LLMFailure("timeout")

    monkeypatch.setattr(goal_agent, "call_json", fake_call_json)
    res = goal_agent.run("Need catering for 100", "INR")
    assert res.parsed is None
    assert res.fallback is True
    assert res.question is not None


def test_discovery_retry_scenario_relaxes_filters_and_finds_lenscraft(db: Session) -> None:
    rows = db.execute(select(Provider)).scalars().all()
    providers = [ProviderOut.model_validate(r) for r in rows]
    needs = [
        Need(key="catering", category="catering", quantity=100),
        Need(key="photography", category="photography"),
    ]

    # Pass 0: strict filters (min_rating=4.5, max_turnaround_days=5)
    f0 = discovery_agent.initial_filters("retry")
    assert f0.min_rating == 4.5
    assert f0.max_turnaround_days == 5
    cands0, rep0 = discovery_agent.run(providers, needs, f0)
    assert [p.name for p in cands0["photography"]] == ["Studio X"]
    assert rep0.counts["photography"] == 1
    assert rep0.sufficient is False

    # Retry 1: drops min_rating
    f1, dropped1 = discovery_agent.relax_filters(f0, 1)
    assert "min_rating" in dropped1
    assert f1.min_rating is None
    assert f1.max_turnaround_days == 5
    cands1, rep1 = discovery_agent.run(providers, needs, f1)
    assert [p.name for p in cands1["photography"]] == ["Studio X"]
    assert rep1.sufficient is False

    # Retry 2: drops max_turnaround_days -> LensCraft appears
    f2, dropped2 = discovery_agent.relax_filters(f1, 2)
    assert "max_turnaround_days" in dropped2
    assert f2.min_rating is None
    assert f2.max_turnaround_days is None
    cands2, rep2 = discovery_agent.run(providers, needs, f2)
    assert [p.name for p in cands2["photography"]] == ["Studio X", "LensCraft"]
    assert rep2.counts["photography"] == 2
    assert rep2.counts["catering"] == 2
    assert rep2.sufficient is True


def test_provider_agent_fallback_and_clean_and_blocked_planning(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = db.execute(select(Provider)).scalars().all()
    providers_list = [ProviderOut.model_validate(r) for r in rows]
    providers_by_id = {p.id: p for p in providers_list}
    needs = [
        Need(key="catering", category="catering", quantity=100),
        Need(key="photography", category="photography"),
    ]

    monkeypatch.setattr(
        provider_agent,
        "call_json",
        lambda *a, **kw: OfferTextLLMOut(scope="Full buffet service", pitch="Best value"),
    )
    monkeypatch.setattr(
        planning_agent,
        "call_json",
        lambda *a, **kw: RationaleLLMOut(
            rationale="Selected top-rated providers with lowest combined cost."
        ),
    )

    # Clean scenario: verified only, budget INR 50,000 (5,000,000 paise)
    cands_clean, _ = discovery_agent.run(
        providers_list,
        needs,
        discovery_agent.initial_filters("clean"),
        include_unverified=False,
    )
    all_offers = []
    for need in needs:
        o, fb = provider_agent.run(need, cands_clean[need.key])
        assert fb is False
        all_offers.extend(o)

    curr = list(all_offers)
    for r in (1, 2, 3):
        curr = negotiation_agent.run_round(curr, providers_by_id, r)
        all_offers.extend(curr)

    plan_clean, plan_fb = planning_agent.run(
        all_offers, needs, providers_by_id, 5_000_000, "INR"
    )
    assert plan_clean is not None
    assert plan_fb is False
    chosen_names = {item.need_key: item.provider_name for item in plan_clean.items}
    assert chosen_names == {"catering": "ABC Catering", "photography": "Studio X"}
    assert plan_clean.total_minor == 2_496_665 + 1_600_001
    assert all(item.verified for item in plan_clean.items)

    # Blocked scenario: include_unverified=True, budget INR 36,000 (3,600,000 paise)
    cands_blocked, rep_blocked = discovery_agent.run(
        providers_list,
        needs,
        discovery_agent.initial_filters("blocked"),
        include_unverified=True,
    )
    # Coverage report still counts ONLY verified providers
    assert rep_blocked.counts == {"catering": 2, "photography": 2}

    blocked_offers = []
    for need in needs:
        o, _ = provider_agent.run(need, cands_blocked[need.key])
        blocked_offers.extend(o)
    for r in (1, 2, 3):
        blocked_offers = negotiation_agent.run_round(blocked_offers, providers_by_id, r)

    plan_blocked, _ = planning_agent.run(
        blocked_offers, needs, providers_by_id, 3_600_000, "INR"
    )
    assert plan_blocked is not None
    assert any(not item.verified for item in plan_blocked.items)
    assert plan_blocked.total_minor <= 3_600_000


def test_provider_and_planning_llm_failure_fallbacks(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = db.execute(select(Provider)).scalars().all()
    providers_list = [ProviderOut.model_validate(r) for r in rows]
    providers_by_id = {p.id: p for p in providers_list}
    need = Need(key="catering", category="catering", quantity=100)

    def fail_llm(*args: Any, **kwargs: Any) -> Any:
        raise LLMFailure("Simulated LLM outage")

    monkeypatch.setattr(provider_agent, "call_json", fail_llm)
    monkeypatch.setattr(planning_agent, "call_json", fail_llm)

    offers, prov_fb = provider_agent.run(need, providers_list[:2])
    assert prov_fb is True
    assert all(o.scope for o in offers)

    plan, plan_fb = planning_agent.run(offers, [need], providers_by_id, 5_000_000, "INR")
    assert plan is not None
    assert plan_fb is True
    assert "ABC Catering" in plan.rationale

    # Budget too low -> returns (None, False)
    no_plan, no_fb = planning_agent.run(offers, [need], providers_by_id, 100_000, "INR")
    assert no_plan is None
    assert no_fb is False
