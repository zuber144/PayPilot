"""Unit tests for `app.orchestration` (state, tools, router, graph)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import db as db_module
from app import llm
from app.config import settings
from app.enums import (
    Action,
    GoalStatus,
    OfferStatus,
    PlanStatus,
    RuleId,
    RuleOutcome,
    TraceNode,
    TraceStatus,
    Verdict,
)
from app.models import Goal, Offer, Plan, Provider
from app.orchestration import graph as graph_module
from app.orchestration import router
from app.orchestration.state import AgentState, append_trace, make_initial_state
from app.orchestration.tools import PERMITTED_ACTIONS, validate_action
from app.schemas import (
    CoverageReport,
    Filters,
    Need,
    OfferDraft,
    ParsedGoal,
    PayGuardResult,
    PlanDraft,
    PlanItem,
    ProviderOut,
    RuleResult,
)


def _sample_need(key: str = "photography") -> Need:
    return Need(key=key, category=key, quantity=1)


def _sample_provider(
    pid: int = 1,
    name: str = "Studio X",
    category: str = "photography",
    base: int = 1_800_000,
    min_p: int = 1_500_000,
    verified: bool = True,
) -> ProviderOut:
    return ProviderOut(
        id=pid,
        name=name,
        category=category,
        base_price_minor=base,
        min_price_minor=min_p,
        concession_rate=0.05,
        rating=4.7,
        turnaround_days=4,
        verified=verified,
        currency="USD",
    )


def test_tools_validate_action() -> None:
    assert Action.DISCOVER in PERMITTED_ACTIONS
    assert validate_action("discover", [Action.DISCOVER, Action.ASK_USER]) == Action.DISCOVER
    assert validate_action("payguard", [Action.DISCOVER, Action.ASK_USER]) is None
    assert validate_action("invent_money", list(PERMITTED_ACTIONS)) is None


def test_router_allowed_actions_table() -> None:
    # 1. After goal parsed
    s1: AgentState = {
        "needs": [_sample_need("catering"), _sample_need("photography")],
        "retries": {"discovery": 0, "negotiation": 0, "plan_revision": 0},
    }
    assert router.allowed_actions(s1) == [Action.DISCOVER, Action.ASK_USER]

    # 2. Coverage below required (retries < 2, minimum met)
    s2: AgentState = {
        "needs": [_sample_need("photography")],
        "coverage": CoverageReport(counts={"photography": 1}, required=2, sufficient=False, minimum_met=True),
        "retries": {"discovery": 0, "negotiation": 0, "plan_revision": 0},
    }
    assert router.allowed_actions(s2) == [
        Action.RETRY_DISCOVERY,
        Action.CONTINUE_WITH_MINIMUM,
        Action.ASK_USER,
    ]

    # 3. Coverage below required, retries exhausted, minimum met -> continue_with_minimum
    s3: AgentState = {
        "needs": [_sample_need("photography")],
        "coverage": CoverageReport(counts={"photography": 1}, required=2, sufficient=False, minimum_met=True),
        "retries": {"discovery": 2, "negotiation": 0, "plan_revision": 0},
    }
    assert router.allowed_actions(s3) == [Action.CONTINUE_WITH_MINIMUM, Action.ASK_USER]

    # 4. Coverage below required, retries exhausted, minimum NOT met -> ask_user
    s4: AgentState = {
        "needs": [_sample_need("photography")],
        "coverage": CoverageReport(counts={"photography": 0}, required=2, sufficient=False, minimum_met=False),
        "retries": {"discovery": 2, "negotiation": 0, "plan_revision": 0},
    }
    assert router.allowed_actions(s4) == [Action.ASK_USER]

    # 5. Offers ready: round 0 -> mandatory comparison pass; after MAX_NEGOTIATION_ROUNDS (1) -> plan
    offer = OfferDraft(need_key="photography", provider_id=1, round=0, price_minor=1_800_000, timeline_days=4)
    s5_first: AgentState = {
        "needs": [_sample_need("photography")],
        "offers": [offer],
        "retries": {"discovery": 0, "negotiation": 0, "plan_revision": 0},
    }
    assert router.allowed_actions(s5_first) == [Action.NEGOTIATE]
    s5: AgentState = {
        "needs": [_sample_need("photography")],
        "offers": [offer],
        "retries": {"discovery": 0, "negotiation": 1, "plan_revision": 0},
    }
    assert router.allowed_actions(s5) == [Action.PLAN]

    s5_done: AgentState = {
        "needs": [_sample_need("photography")],
        "offers": [offer],
        "retries": {"discovery": 0, "negotiation": 3, "plan_revision": 0},
    }
    assert router.allowed_actions(s5_done) == [Action.PLAN]

    # 6. No plan within budget (revisions < 1 vs revisions == 1)
    s6: AgentState = {
        "needs": [_sample_need("photography")],
        "offers": [offer],
        "plan": None,
        "stage": "planned",
        "retries": {"discovery": 0, "negotiation": 3, "plan_revision": 0},
    }
    assert router.allowed_actions(s6) == [Action.REVISE_PLAN, Action.ASK_USER]

    s6_exhausted: AgentState = {
        "needs": [_sample_need("photography")],
        "offers": [offer],
        "plan": None,
        "stage": "planned",
        "retries": {"discovery": 0, "negotiation": 4, "plan_revision": 1},
    }
    assert router.allowed_actions(s6_exhausted) == [Action.ASK_USER]

    # 7. Plan ready -> payguard
    plan = PlanDraft(
        items=[
            PlanItem(
                need_key="photography",
                provider_id=1,
                provider_name="Studio X",
                price_minor=1_600_000,
                timeline_days=4,
                verified=True,
            )
        ],
        total_minor=1_600_000,
        currency="USD",
        rationale="Best option",
    )
    s7: AgentState = {
        "needs": [_sample_need("photography")],
        "offers": [offer],
        "plan": plan,
        "retries": {"discovery": 0, "negotiation": 3, "plan_revision": 0},
    }
    assert router.allowed_actions(s7) == [Action.PAYGUARD]


def test_router_choose_action_falls_back_on_invalid_pick_or_llm_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    state: AgentState = {
        "needs": [_sample_need("photography")],
        "retries": {"discovery": 0, "negotiation": 0, "plan_revision": 0},
    }
    # Disallowed action returned by LLM
    monkeypatch.setattr(
        llm,
        "_raw_completion",
        lambda s, u, t: json.dumps({"action": "payguard", "reason": "skip everything"}),
    )
    action, fb, reason = router.choose_action(state)
    assert action == Action.DISCOVER
    assert fb is True
    assert "disallowed" in reason.lower()

    # LLMFailure raised by LLM
    def raise_timeout(s: str, u: str, t: str) -> str:
        raise TimeoutError("timeout")

    monkeypatch.setattr(llm, "_raw_completion", raise_timeout)
    action2, fb2, reason2 = router.choose_action(state)
    assert action2 == Action.DISCOVER
    assert fb2 is True
    assert "failed" in reason2.lower()


def test_graph_retry_and_persistence_with_mocked_agents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    eng = db_module.init_engine(f"sqlite:///{tmp_path / 'orch.db'}")
    try:
        with db_module.SessionLocal() as s:
            s.add_all(
                [
                    Provider(
                        id=1,
                        name="Studio X",
                        category="photography",
                        base_price_minor=1_800_000,
                        min_price_minor=1_500_000,
                        concession_rate=0.04,
                        rating=4.7,
                        turnaround_days=4,
                        verified=True,
                        currency="USD",
                    ),
                    Provider(
                        id=2,
                        name="LensCraft",
                        category="photography",
                        base_price_minor=2_100_000,
                        min_price_minor=1_750_000,
                        concession_rate=0.04,
                        rating=4.2,
                        turnaround_days=9,
                        verified=True,
                        currency="USD",
                    ),
                ]
            )
            goal = Goal(
                raw_text="Photographer for corporate event",
                budget_minor=3_000_000,
                currency="USD",
                scenario="retry",
                status=GoalStatus.RUNNING.value,
                trace=[],
            )
            s.add(goal)
            s.commit()
            gid = goal.id

        fake_goal_agent = SimpleNamespace(
            run=lambda raw_text, currency: SimpleNamespace(
                parsed=ParsedGoal(needs=[_sample_need("photography")], deadline_days=10, currency=currency),
                question=None,
                fallback=False,
                reason="Parsed photography need",
            )
        )

        def fake_discover_run(
            providers: list[ProviderOut],
            needs: list[Need],
            filters: Filters,
            *,
            include_unverified: bool = False,
        ) -> tuple[dict[str, list[ProviderOut]], CoverageReport]:
            matched = [
                p
                for p in providers
                if (filters.min_rating is None or p.rating >= filters.min_rating)
                and (filters.max_turnaround_days is None or p.turnaround_days <= filters.max_turnaround_days)
            ]
            cov = CoverageReport(
                counts={"photography": len(matched)},
                required=2,
                sufficient=len(matched) >= 2,
                minimum_met=len(matched) >= 1,
            )
            return {"photography": matched}, cov

        def fake_relax(filters: Filters, attempt: int) -> tuple[Filters, list[str]]:
            if attempt == 1:
                return Filters(min_rating=None, max_turnaround_days=filters.max_turnaround_days), ["min_rating"]
            return Filters(min_rating=None, max_turnaround_days=None), ["max_turnaround_days"]

        fake_discovery_agent = SimpleNamespace(
            initial_filters=lambda scenario: (
                Filters(min_rating=4.5, max_turnaround_days=5) if scenario == "retry" else Filters()
            ),
            relax_filters=fake_relax,
            run=fake_discover_run,
        )

        fake_provider_agent = SimpleNamespace(
            run=lambda need, provs: (
                [
                    OfferDraft(
                        need_key=need.key,
                        provider_id=p.id,
                        round=0,
                        price_minor=p.base_price_minor,
                        timeline_days=p.turnaround_days,
                        scope=f"Offer by {p.name}",
                        status=OfferStatus.OPEN,
                    )
                    for p in provs
                ],
                False,
            )
        )

        fake_negotiation_agent = SimpleNamespace(
            run_round=lambda offers, providers, round_no: [
                OfferDraft(
                    need_key=o.need_key,
                    provider_id=o.provider_id,
                    round=round_no,
                    price_minor=max(providers[o.provider_id].min_price_minor, o.price_minor - 50_000),
                    counter_minor=int(o.price_minor * 0.9),
                    timeline_days=o.timeline_days,
                    scope=o.scope,
                    status=OfferStatus.COUNTERED,
                )
                for o in offers
            ]
        )

        fake_planning_agent = SimpleNamespace(
            run=lambda final_offers, needs, providers, budget_minor, currency: (
                PlanDraft(
                    items=[
                        PlanItem(
                            need_key="photography",
                            provider_id=1,
                            provider_name="Studio X",
                            price_minor=final_offers[0].price_minor,
                            timeline_days=4,
                            verified=True,
                            currency=currency,
                        )
                    ],
                    total_minor=final_offers[0].price_minor,
                    currency=currency,
                    rationale="Picked Studio X",
                ),
                False,
            )
        )

        fake_payguard_engine = SimpleNamespace(
            run_payguard=lambda plan, budget, curr, text, provs, other: PayGuardResult(
                verdict=Verdict.APPROVED,
                risk_score=0.1,
                ai_ok=True,
                flags=[],
                rules=[RuleResult(id=RuleId.BUDGET_CAP.value, result=RuleOutcome.PASS, detail="Within budget")],
            )
        )

        monkeypatch.setattr(graph_module, "goal_agent", fake_goal_agent)
        monkeypatch.setattr(graph_module, "discovery_agent", fake_discovery_agent)
        monkeypatch.setattr(graph_module, "provider_agent", fake_provider_agent)
        monkeypatch.setattr(graph_module, "negotiation_agent", fake_negotiation_agent)
        monkeypatch.setattr(graph_module, "planning_agent", fake_planning_agent)
        monkeypatch.setattr(graph_module, "payguard_engine", fake_payguard_engine)

        graph_module.run_workflow(gid)

        with db_module.SessionLocal() as s:
            saved_goal = s.get(Goal, gid)
            assert saved_goal is not None
            assert saved_goal.status == GoalStatus.PLAN_READY.value
            retry_events = [e for e in saved_goal.trace if e["status"] == TraceStatus.RETRY.value]
            assert len(retry_events) == 2
            assert "Coverage < 2 for need 'photography'; retry 1 of 2" in retry_events[0]["reason"]
            assert retry_events[0]["data"]["relaxed"] == ["min_rating"]

            plans = s.query(Plan).filter(Plan.goal_id == gid).all()
            assert len(plans) == 1
            assert plans[0].status == PlanStatus.CHECKED.value
            assert plans[0].payguard_result is not None
            assert plans[0].payguard_result["verdict"] == Verdict.APPROVED.value

            offers = s.query(Offer).filter(Offer.goal_id == gid).all()
            assert len(offers) == 4  # 2 listings * (round 0 + 1 comparison pass)
            selected = [o for o in offers if o.status == OfferStatus.SELECTED.value]
            assert len(selected) == 1
            assert selected[0].provider_id == 1
            assert selected[0].round == 1

            actions = [e["action"] for e in saved_goal.trace]
            assert actions.count("web_search") == 1  # searched once; retries only re-filter
            assert actions.index("web_search") < actions.index("discover_listings")
    finally:
        eng.dispose()


def test_graph_enforces_max_graph_steps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    eng = db_module.init_engine(f"sqlite:///{tmp_path / 'steps.db'}")
    try:
        monkeypatch.setattr(settings, "MAX_GRAPH_STEPS", 2)
        with db_module.SessionLocal() as s:
            goal = Goal(
                raw_text="Catering for 100 people",
                budget_minor=5_000_000,
                currency="USD",
                status=GoalStatus.RUNNING.value,
                trace=[],
            )
            s.add(goal)
            s.commit()
            gid = goal.id

        fake_goal_agent = SimpleNamespace(
            run=lambda raw_text, currency: SimpleNamespace(
                parsed=ParsedGoal(needs=[_sample_need("catering")], deadline_days=5, currency=currency),
                question=None,
                fallback=False,
                reason="ok",
            )
        )
        fake_discovery_agent = SimpleNamespace(
            initial_filters=lambda scenario: Filters(),
            relax_filters=lambda f, a: (f, []),
            run=lambda provs, needs, filters, include_unverified=False: (
                {"catering": []},
                CoverageReport(counts={"catering": 0}, required=2, sufficient=False, minimum_met=False),
            ),
        )
        monkeypatch.setattr(graph_module, "goal_agent", fake_goal_agent)
        monkeypatch.setattr(graph_module, "discovery_agent", fake_discovery_agent)

        graph_module.run_workflow(gid)

        with db_module.SessionLocal() as s:
            saved = s.get(Goal, gid)
            assert saved is not None
            assert saved.status == GoalStatus.FAILED.value
            assert any(e["status"] == TraceStatus.ERROR.value for e in saved.trace)
    finally:
        eng.dispose()


def test_append_trace_increments_seq() -> None:
    state = make_initial_state(goal_id=1, raw_text="test", budget_minor=1000)
    e1 = append_trace(state, node=TraceNode.GOAL, action="parse", status=TraceStatus.OK, summary="s1")
    e2 = append_trace(state, node=TraceNode.ORCHESTRATOR, action="discover", status=TraceStatus.OK, summary="s2")
    assert e1.seq == 1
    assert e2.seq == 2
    assert len(state["trace"]) == 2


def test_real_agents_clean_retry_blocked_review_workflows(db) -> None:  # type: ignore[no-untyped-def]
    shopping_text = "Birthday party supplies: 10 party hats and 50 balloons, needed within 5 days"
    budget = 2_000  # USD 20.00

    def run(raw_text: str, scenario: str) -> Goal:
        g = Goal(
            raw_text=raw_text,
            budget_minor=budget,
            currency="USD",
            scenario=scenario,
            status=GoalStatus.RUNNING.value,
            trace=[],
        )
        db.add(g)
        db.commit()
        graph_module.run_workflow(g.id)
        db.expire_all()
        out = db.get(Goal, g.id)
        assert out is not None
        return out

    # 1. Clean -> PLAN_READY, cheapest verified listing per item (shipping included), APPROVED
    g_clean = run(shopping_text, "clean")
    assert g_clean.status == GoalStatus.PLAN_READY.value
    actions = [e["action"] for e in g_clean.trace]
    assert "web_search" in actions and "compare_prices_round_1" in actions
    plan_clean = db.query(Plan).filter(Plan.goal_id == g_clean.id).one()
    assert plan_clean.status == PlanStatus.CHECKED.value
    assert sorted(i["provider_name"] for i in plan_clean.items) == [
        "Balloon Bazaar (Amazon)",
        "PartyZone Official (Flipkart)",
    ]
    assert plan_clean.total_minor == 583
    hats = next(i for i in plan_clean.items if i["need_key"] == "party_hats")
    assert (hats["packs"], hats["pack_price_minor"], hats["shipping_minor"], hats["price_minor"]) == (1, 298, 48, 346)
    assert hats["original_currency"] == "INR" and hats["original_price_minor"] == 29_000  # INR 250 + 40
    assert plan_clean.payguard_result is not None
    assert plan_clean.payguard_result["verdict"] == Verdict.APPROVED.value

    # 2. Retry -> RETRY trace event + the relaxed-filter hat listing offered
    g_retry = run(shopping_text, "retry")
    assert g_retry.status == GoalStatus.PLAN_READY.value
    retries = [e for e in g_retry.trace if e["status"] == TraceStatus.RETRY.value]
    assert len(retries) >= 1
    retry_offers = db.query(Offer).filter(Offer.goal_id == g_retry.id).all()
    partyzone = db.query(Provider).filter(Provider.name == "PartyZone Official (Flipkart)").one()
    assert any(o.provider_id == partyzone.id for o in retry_offers)

    # 3. Blocked -> unverified sellers included by discovery; VERIFIED_PROVIDER = BLOCK, verdict BLOCKED
    g_blocked = run(shopping_text, "blocked")
    plan_blocked = db.query(Plan).filter(Plan.goal_id == g_blocked.id).one()
    assert plan_blocked.payguard_result is not None
    assert plan_blocked.payguard_result["verdict"] == Verdict.BLOCKED.value
    rules = {r["id"]: r["result"] for r in plan_blocked.payguard_result["rules"]}
    assert rules[RuleId.VERIFIED_PROVIDER.value] == RuleOutcome.BLOCK.value

    # 4. Review -> single item, one seller holds 100%: SINGLE_VENDOR_SHARE = REVIEW, verdict REVIEW
    g_review = run("Office party: 20 party hats", "review")
    plan_review = db.query(Plan).filter(Plan.goal_id == g_review.id).one()
    assert plan_review.payguard_result is not None
    assert plan_review.payguard_result["verdict"] == Verdict.REVIEW.value
    (item,) = plan_review.items
    assert item["packs"] == 2  # 20 hats / pack of 10
    assert item["price_minor"] == 2 * 298 + 48
