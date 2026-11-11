"""Focused unit tests for goal_agent, discovery_agent, provider_agent, planning_agent, and seed."""

from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import (
    discovery_agent,
    goal_agent,
    negotiation_agent,
    planning_agent,
    provider_agent,
)
from app.llm import LLMFailure
from app.models import Provider, User
from app.schemas import (
    GoalLLMOut,
    Need,
    OfferDraft,
    OfferTextLLMOut,
    ProviderOut,
    RationaleLLMOut,
)
from app.search.catalog import CATALOG
from seed import seed

NEEDS = [
    Need(key="party_hats", category="party_hats", quantity=10),
    Need(key="balloons", category="balloons", quantity=50),
]


def _catalog(db: Session) -> list[ProviderOut]:
    rows = db.execute(select(Provider).order_by(Provider.id)).scalars().all()
    return [ProviderOut.model_validate(r) for r in rows]


def test_seed_is_idempotent(db: Session) -> None:
    seed(db)
    seed(db)
    providers = db.execute(select(Provider)).scalars().all()
    users = db.execute(select(User)).scalars().all()
    assert len(providers) == len(CATALOG) == 6
    assert all(p.source == "catalog" for p in providers)
    assert len(users) == 1


def test_goal_agent_parses_unique_needs_and_defaults_currency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_call_json(system: str, user: str, schema_model: Any, *, task: str) -> GoalLLMOut:
        assert task == "goal_parse"
        return GoalLLMOut(
            needs=[
                Need(key="party_hats", category="party_hats", quantity=10),
                Need(key="party_hats", category="party_hats", quantity=5),  # duplicate key
                Need(key="balloons", category="balloons", quantity=50),
            ],
            deadline_days=5,
            currency=None,
        )

    monkeypatch.setattr(goal_agent, "call_json", fake_call_json)
    res = goal_agent.run("Need 10 party hats and 50 balloons", "USD")
    assert res.parsed is not None
    assert res.fallback is False
    assert res.question is None
    assert res.parsed.currency == "USD"
    assert [n.key for n in res.parsed.needs] == ["party_hats", "balloons"]
    assert res.parsed.needs[0].quantity == 10


def test_goal_agent_empty_needs_sets_question(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_call_json(system: str, user: str, schema_model: Any, *, task: str) -> GoalLLMOut:
        return GoalLLMOut(needs=[], question="Which products do you need?")

    monkeypatch.setattr(goal_agent, "call_json", fake_call_json)
    res = goal_agent.run("Help me plan something", "USD")
    assert res.parsed is None
    assert res.fallback is False
    assert res.question == "Which products do you need?"


def test_goal_agent_llm_failure_sets_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_call_json(system: str, user: str, schema_model: Any, *, task: str) -> GoalLLMOut:
        raise LLMFailure("timeout")

    monkeypatch.setattr(goal_agent, "call_json", fake_call_json)
    res = goal_agent.run("Need 10 party hats", "USD")
    assert res.parsed is None
    assert res.fallback is True
    assert res.question is not None


def test_discovery_retry_scenario_relaxes_filters_and_finds_partyzone(db: Session) -> None:
    providers = _catalog(db)

    # Pass 0: strict filters (min_rating=4.5, max_turnaround_days=5) -> no verified hats
    f0 = discovery_agent.initial_filters("retry")
    assert f0.min_rating == 4.5
    assert f0.max_turnaround_days == 5
    cands0, rep0 = discovery_agent.run(providers, NEEDS, f0)
    assert cands0["party_hats"] == []
    assert [p.name for p in cands0["balloons"]] == ["Balloon Bazaar (Amazon)"]
    assert rep0.counts == {"party_hats": 0, "balloons": 1}
    assert rep0.sufficient is False

    # Retry 1: drops min_rating -> PartyZone appears, coverage sufficient
    f1, dropped1 = discovery_agent.relax_filters(f0, 1)
    assert "min_rating" in dropped1
    assert f1.min_rating is None
    assert f1.max_turnaround_days == 5
    cands1, rep1 = discovery_agent.run(providers, NEEDS, f1)
    assert [p.name for p in cands1["party_hats"]] == [
        "Celebrations Hub (Amazon)",
        "PartyZone Official (Flipkart)",
    ]
    assert rep1.counts == {"party_hats": 2, "balloons": 2}
    assert rep1.sufficient is True

    # Unverified Meesho sellers are never candidates without include_unverified
    assert all(p.verified for c in cands1.values() for p in c)

    # Retry 2 also drops max_turnaround_days
    f2, dropped2 = discovery_agent.relax_filters(f1, 2)
    assert "max_turnaround_days" in dropped2
    assert f2.max_turnaround_days is None


def _offers_and_compare(
    cands: dict[str, list[ProviderOut]], providers_by_id: dict[int, ProviderOut]
) -> list[OfferDraft]:
    offers: list[OfferDraft] = []
    for need in NEEDS:
        o, fb = provider_agent.run(need, cands[need.key])
        assert fb is False
        offers.extend(o)
    return negotiation_agent.run_round(offers, providers_by_id, 1)


def test_provider_agent_fallback_and_clean_and_blocked_planning(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    providers_list = _catalog(db)
    providers_by_id = {p.id: p for p in providers_list}

    monkeypatch.setattr(
        provider_agent,
        "call_json",
        lambda *a, **kw: OfferTextLLMOut(scope="Pack of party supplies", pitch=""),
    )
    monkeypatch.setattr(
        planning_agent,
        "call_json",
        lambda *a, **kw: RationaleLLMOut(rationale="Cheapest verified cart."),
    )

    # Clean scenario: verified only, budget USD 20.00
    cands_clean, _ = discovery_agent.run(
        providers_list, NEEDS, discovery_agent.initial_filters("clean"), include_unverified=False
    )
    compared = _offers_and_compare(cands_clean, providers_by_id)
    plan_clean, plan_fb = planning_agent.run(compared, NEEDS, providers_by_id, 2_000, "USD")
    assert plan_clean is not None
    assert plan_fb is False
    chosen = {item.need_key: item.provider_name for item in plan_clean.items}
    assert chosen == {
        "party_hats": "PartyZone Official (Flipkart)",
        "balloons": "Balloon Bazaar (Amazon)",
    }
    # 25000 paise -> 298 cents + 4000 paise shipping -> 48 cents; 19900 paise -> 237 cents
    assert plan_clean.total_minor == 298 + 48 + 237 == 583
    assert all(item.verified for item in plan_clean.items)
    hats = next(i for i in plan_clean.items if i.need_key == "party_hats")
    assert hats.packs == 1
    assert hats.store == "flipkart"
    assert hats.original_price_minor == 25_000 + 4_000

    # Blocked scenario: include_unverified=True -> cheapest is the unverified Meesho sellers
    cands_blocked, rep_blocked = discovery_agent.run(
        providers_list, NEEDS, discovery_agent.initial_filters("blocked"), include_unverified=True
    )
    # Coverage report still counts ONLY verified listings
    assert rep_blocked.counts == {"party_hats": 2, "balloons": 2}
    compared_b = _offers_and_compare(cands_blocked, providers_by_id)
    plan_blocked, _ = planning_agent.run(compared_b, NEEDS, providers_by_id, 2_000, "USD")
    assert plan_blocked is not None
    assert all(not item.verified for item in plan_blocked.items)
    assert plan_blocked.total_minor == 179 + 118
    assert {i.store for i in plan_blocked.items} == {"meesho"}


def test_provider_agent_packs_scale_with_quantity(db: Session) -> None:
    hats = [p for p in _catalog(db) if p.category == "party_hats" and p.verified]
    names = {p.id: p.name for p in hats}
    offers, _ = provider_agent.run(Need(key="party_hats", category="party_hats", quantity=20), hats)
    pz = next(o for o in offers if names[o.provider_id] == "PartyZone Official (Flipkart)")
    assert pz.round == 0
    assert pz.packs == 2
    assert pz.price_minor == 2 * 298 + 48
    assert pz.pack_price_minor == 298
    assert pz.shipping_minor == 48
    # No quantity -> one pack
    offers1, _ = provider_agent.run(Need(key="party_hats", category="party_hats"), hats)
    assert all(o.packs == 1 for o in offers1)
    # Ceil: 11 hats with packs of 10 -> 2 packs
    assert provider_agent.packs_needed(11, 10) == 2
    assert provider_agent.packs_needed(10, 10) == 1
    assert provider_agent.packs_needed(None, 10) == 1


def test_provider_and_planning_llm_failure_fallbacks(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    providers_list = _catalog(db)
    providers_by_id = {p.id: p for p in providers_list}
    need = Need(key="party_hats", category="party_hats", quantity=10)
    hats = [p for p in providers_list if p.category == "party_hats" and p.verified]

    def fail_llm(*args: Any, **kwargs: Any) -> Any:
        raise LLMFailure("Simulated LLM outage")

    monkeypatch.setattr(provider_agent, "call_json", fail_llm)
    monkeypatch.setattr(planning_agent, "call_json", fail_llm)

    offers, prov_fb = provider_agent.run(need, hats)
    assert prov_fb is True
    assert all(o.scope for o in offers)

    plan, plan_fb = planning_agent.run(offers, [need], providers_by_id, 2_000, "USD")
    assert plan is not None
    assert plan_fb is True
    assert "PartyZone Official (Flipkart)" in plan.rationale
    assert "USD 3.46" in plan.rationale

    # Budget too low -> returns (None, False)
    no_plan, no_fb = planning_agent.run(offers, [need], providers_by_id, 100, "USD")
    assert no_plan is None
    assert no_fb is False
