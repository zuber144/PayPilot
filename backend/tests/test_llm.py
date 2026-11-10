"""Tests for LLM gateway validation, retries, timeouts, and agent fallbacks."""

import pytest

from app import llm
from app.agents import goal_agent
from app.enums import Action, RuleOutcome, Verdict
from app.llm import LLMFailure
from app.orchestration import router
from app.payguard import engine, policy, risk
from app.schemas import CoverageReport, Filters, GoalLLMOut, Need, PlanDraft, PlanItem, ProviderOut


def test_llm_invalid_json_and_timeout_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Section 15 #8: LLM invalid JSON or timeout —
    Schema validation and fallback behaviour work safely:
    - call_json raises LLMFailure on invalid JSON and on timeout
    - Goal Agent falls back to parsed=None with a clarification question (NEEDS_INPUT)
    - Router falls back to the default action with a FALLBACK trace status
    - Risk assessment falls back to ai_ok=False and caps PayGuard verdict at REVIEW
    """
    # 1. Invalid JSON -> LLMFailure
    monkeypatch.setattr(llm, "_raw_completion", lambda system, user, task: "{not valid json")
    with pytest.raises(LLMFailure):
        llm.call_json("sys", "{}", GoalLLMOut, task="goal_parse")

    # Goal agent fallback on invalid JSON
    goal_res = goal_agent.run("Corporate event in Bangalore", "INR")
    assert goal_res.parsed is None
    assert goal_res.question is not None and len(goal_res.question) > 0
    assert goal_res.fallback is True

    # 2. Timeout -> LLMFailure
    def raise_timeout(system: str, user: str, task: str) -> str:
        raise TimeoutError("OpenAI request timed out")

    monkeypatch.setattr(llm, "_raw_completion", raise_timeout)
    with pytest.raises(LLMFailure):
        llm.call_json("sys", "{}", GoalLLMOut, task="goal_parse")

    # Router fallback on timeout -> picks default action and marks FALLBACK
    state = {
        "goal_id": 1,
        "raw_text": "Event",
        "budget_minor": 5_000_000,
        "currency": "INR",
        "needs": [Need(key="catering", category="catering", quantity=100)],
        "filters": Filters().model_dump(),
        "candidates": {},
        "coverage": CoverageReport(
            counts={"catering": 1}, required=2, sufficient=False, minimum_met=True
        ).model_dump(),
        "offers": [],
        "plan": None,
        "payguard": None,
        "retries": {"discovery": 0, "negotiation": 0, "plan_revision": 0},
        "trace": [],
        "status": "RUNNING",
        "next_action": None,
    }
    allowed = router.allowed_actions(state)  # type: ignore[arg-type]
    default_action = router.default_action(state)  # type: ignore[arg-type]
    assert Action.RETRY_DISCOVERY in allowed
    assert default_action == Action.RETRY_DISCOVERY
    chosen_action, fallback_used, _reason = router.choose_action(state)  # type: ignore[arg-type]
    assert chosen_action == default_action
    assert fallback_used is True

    # Risk fallback on timeout -> ai_ok=False, verdict capped at REVIEW
    plan = PlanDraft(
        items=[
            PlanItem(
                need_key="catering",
                provider_id=1,
                provider_name="ABC Catering",
                price_minor=2_500_000,
                timeline_days=7,
                verified=True,
                currency="INR",
            ),
            PlanItem(
                need_key="photography",
                provider_id=2,
                provider_name="Studio X",
                price_minor=1_600_000,
                timeline_days=4,
                verified=True,
                currency="INR",
            ),
        ],
        total_minor=4_100_000,
        currency="INR",
    )
    providers = {
        1: ProviderOut(
            id=1,
            name="ABC Catering",
            category="catering",
            base_price_minor=2_800_000,
            min_price_minor=2_400_000,
            concession_rate=0.0375,
            rating=4.6,
            turnaround_days=7,
            verified=True,
            currency="INR",
        ),
        2: ProviderOut(
            id=2,
            name="Studio X",
            category="photography",
            base_price_minor=1_800_000,
            min_price_minor=1_500_000,
            concession_rate=0.0385,
            rating=4.7,
            turnaround_days=4,
            verified=True,
            currency="INR",
        ),
    }
    score, flags, ai_ok = risk.assess(plan, "Corporate event", 5_000_000)
    assert ai_ok is False
    assert score is None
    pol = policy.evaluate(plan, 5_000_000, "INR", providers, [])
    pg = engine.combine(pol, score, flags, ai_ok)
    assert pg.verdict == Verdict.REVIEW
    assert any(r.result == RuleOutcome.REVIEW for r in pg.rules)
