"""Tests for PayGuard engine combination and deterministic veto over AI risk."""

import pytest

from app import llm
from app.enums import RuleId, RuleOutcome, Verdict
from app.payguard import engine, policy
from app.schemas import Flag, PlanDraft, PlanItem, ProviderOut


def _providers() -> dict[int, ProviderOut]:
    return {
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


def _clean_plan() -> PlanDraft:
    return PlanDraft(
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
        rationale="Clean plan.",
    )


def test_ai_failure_caps_verdict_at_review(monkeypatch: pytest.MonkeyPatch) -> None:
    """Work-division 3.9 & Section 15 #8: When AI risk call fails, ai_ok=False and verdict is capped at REVIEW."""
    def broken_raw(system: str, user: str, task: str) -> str:
        raise TimeoutError("simulated LLM timeout")

    monkeypatch.setattr(llm, "_raw_completion", broken_raw)

    plan = _clean_plan()
    res = engine.run_payguard(
        plan=plan,
        goal_budget_minor=5_000_000,
        goal_currency="INR",
        goal_text="Corporate event catering and photography",
        providers=_providers(),
        other_plan_statuses=[],
    )
    assert res.ai_ok is False
    assert res.verdict == Verdict.REVIEW
    by_id = {r.id: r for r in res.rules}
    assert by_id[RuleId.AI_RISK_HIGH].result == RuleOutcome.REVIEW
    assert by_id[RuleId.AI_RISK_MEDIUM].result == RuleOutcome.REVIEW
    ack_flag_ids = {f.id for f in res.flags if f.requires_ack}
    assert RuleId.AI_RISK_HIGH in ack_flag_ids
    assert RuleId.AI_RISK_MEDIUM in ack_flag_ids


def test_ai_cannot_override_deterministic_block() -> None:
    """Work-division 3.9: Even if AI risk score is 0.0, a deterministic BLOCK rule forces Verdict.BLOCKED."""
    plan = _clean_plan()
    # Over budget -> BUDGET_CAP BLOCK
    policy_results = policy.evaluate(plan, 3_000_000, "INR", _providers(), [])
    combined = engine.combine(policy_results, risk_score=0.01, ai_flags=[], ai_ok=True)
    assert combined.verdict == Verdict.BLOCKED


def test_ai_high_and_medium_thresholds() -> None:
    """High risk score (>= 0.7) -> BLOCKED; medium risk score (0.4..0.7) -> REVIEW."""
    plan = _clean_plan()
    policy_results = policy.evaluate(plan, 5_000_000, "INR", _providers(), [])

    med = engine.combine(
        policy_results,
        risk_score=0.55,
        ai_flags=[Flag(id="AI:TIMELINE", source="AI", message="Tight timeline", requires_ack=False)],
        ai_ok=True,
    )
    assert med.verdict == Verdict.REVIEW

    high = engine.combine(policy_results, risk_score=0.85, ai_flags=[], ai_ok=True)
    assert high.verdict == Verdict.BLOCKED
    assert len(high.rules) == 10
