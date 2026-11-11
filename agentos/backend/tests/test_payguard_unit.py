"""Focused unit tests for app/payguard (policy.py, risk.py, engine.py)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import llm
from app.config import settings
from app.db import Base
from app.enums import ErrorCode, PlanStatus, RuleId, RuleOutcome, Verdict
from app.errors import ApiError
from app.models import Goal, Plan, Provider
from app.payguard import engine, policy, risk
from app.schemas import Flag, PlanDraft, PlanItem, ProviderOut, RiskFlagLLM, RiskLLMOut


def _providers() -> dict[int, ProviderOut]:
    return {
        1: ProviderOut(
            id=1,
            name="ABC Catering",
            category="catering",
            base_price_minor=2_500_000,
            min_price_minor=2_500_000,
            concession_rate=0.0375,
            rating=4.6,
            turnaround_days=7,
            verified=True,
            currency="USD",
        ),
        2: ProviderOut(
            id=2,
            name="Studio X",
            category="photography",
            base_price_minor=1_600_000,
            min_price_minor=1_600_000,
            concession_rate=0.0385,
            rating=4.7,
            turnaround_days=4,
            verified=True,
            currency="USD",
        ),
        3: ProviderOut(
            id=3,
            name="QuickBites Co",
            category="catering",
            base_price_minor=2_200_000,
            min_price_minor=2_200_000,
            concession_rate=0.03,
            rating=4.1,
            turnaround_days=5,
            verified=False,
            currency="USD",
        ),
    }


def _clean_plan() -> PlanDraft:
    # 2,500,000 (60.98%) + 1,600,000 (39.02%) = 4,100,000
    return PlanDraft(
        items=[
            PlanItem(
                need_key="catering",
                provider_id=1,
                provider_name="ABC Catering",
                price_minor=2_500_000,
                timeline_days=7,
                verified=True,
                currency="USD",
            ),
            PlanItem(
                need_key="photography",
                provider_id=2,
                provider_name="Studio X",
                price_minor=1_600_000,
                timeline_days=4,
                verified=True,
                currency="USD",
            ),
        ],
        total_minor=4_100_000,
        currency="USD",
        rationale="Best balanced combination",
    )


def _rule_map(results: list) -> dict[str, RuleOutcome]:
    return {r.id: r.result for r in results}


def test_policy_all_pass_in_enum_order() -> None:
    res = policy.evaluate(_clean_plan(), 5_000_000, "USD", _providers(), [])
    expected_ids = [
        RuleId.BUDGET_CAP,
        RuleId.TXN_LIMIT,
        RuleId.VERIFIED_PROVIDER,
        RuleId.CURRENCY_MATCH,
        RuleId.NO_DUPLICATE,
        RuleId.PRICE_FLOOR,
        RuleId.TOTAL_INTEGRITY,
        RuleId.SINGLE_VENDOR_SHARE,
    ]
    assert [r.id for r in res] == [rid.value for rid in expected_ids]
    assert all(r.result == RuleOutcome.PASS for r in res)


def test_budget_cap_pass_and_fail() -> None:
    provs = _providers()
    plan = _clean_plan()
    # Exact budget passes
    assert _rule_map(policy.evaluate(plan, 4_100_000, "USD", provs, []))[RuleId.BUDGET_CAP] == RuleOutcome.PASS
    # Over budget blocks
    assert _rule_map(policy.evaluate(plan, 4_099_999, "USD", provs, []))[RuleId.BUDGET_CAP] == RuleOutcome.BLOCK


def test_empty_plan_and_zero_total_block() -> None:
    provs = _providers()
    empty_plan = PlanDraft(items=[], total_minor=0, currency="USD")
    res_empty = policy.evaluate(empty_plan, 5_000_000, "USD", provs, [])
    rmap = _rule_map(res_empty)
    assert rmap[RuleId.BUDGET_CAP] == RuleOutcome.BLOCK
    assert rmap[RuleId.TOTAL_INTEGRITY] == RuleOutcome.BLOCK
    combined = engine.combine(res_empty, 0.1, [], True)
    assert combined.verdict == Verdict.BLOCKED

    zero_total_plan = _clean_plan().model_copy(update={"total_minor": 0})
    res_zero = policy.evaluate(zero_total_plan, 5_000_000, "USD", provs, [])
    rmap_zero = _rule_map(res_zero)
    assert rmap_zero[RuleId.BUDGET_CAP] == RuleOutcome.BLOCK
    assert rmap_zero[RuleId.TOTAL_INTEGRITY] == RuleOutcome.BLOCK


def test_txn_limit_pass_and_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    provs = _providers()
    plan = _clean_plan()
    monkeypatch.setattr(settings, "MAX_TXN_MINOR", 4_100_000)
    assert _rule_map(policy.evaluate(plan, 5_000_000, "USD", provs, []))[RuleId.TXN_LIMIT] == RuleOutcome.PASS

    monkeypatch.setattr(settings, "MAX_TXN_MINOR", 4_000_000)
    assert _rule_map(policy.evaluate(plan, 5_000_000, "USD", provs, []))[RuleId.TXN_LIMIT] == RuleOutcome.BLOCK


def test_verified_provider_uses_db_providers_not_item_claim() -> None:
    provs = _providers()
    # Item claims verified=True for provider 3, which is verified=False in catalogue
    spoofed = PlanDraft(
        items=[
            PlanItem(
                need_key="catering",
                provider_id=3,
                provider_name="QuickBites Co",
                price_minor=2_200_000,
                timeline_days=5,
                verified=True,
                currency="USD",
            ),
            PlanItem(
                need_key="photography",
                provider_id=2,
                provider_name="Studio X",
                price_minor=1_600_000,
                timeline_days=4,
                verified=True,
                currency="USD",
            ),
        ],
        total_minor=3_800_000,
        currency="USD",
    )
    rmap = _rule_map(policy.evaluate(spoofed, 5_000_000, "USD", provs, []))
    assert rmap[RuleId.VERIFIED_PROVIDER] == RuleOutcome.BLOCK

    # Unknown provider ID also blocks VERIFIED_PROVIDER and PRICE_FLOOR
    unknown_plan = spoofed.model_copy(
        update={
            "items": [
                spoofed.items[0].model_copy(update={"provider_id": 999}),
                spoofed.items[1],
            ]
        }
    )
    rmap_unknown = _rule_map(policy.evaluate(unknown_plan, 5_000_000, "USD", provs, []))
    assert rmap_unknown[RuleId.VERIFIED_PROVIDER] == RuleOutcome.BLOCK
    assert rmap_unknown[RuleId.PRICE_FLOOR] == RuleOutcome.BLOCK


def test_currency_match_pass_and_fail() -> None:
    provs = _providers()
    plan = _clean_plan()
    #Unsupported goal currency
    assert _rule_map(policy.evaluate(plan, 5_000_000, "EUR", provs, []))[RuleId.CURRENCY_MATCH] == RuleOutcome.BLOCK
    # Plan currency != goal currency
    bad_plan_curr = plan.model_copy(update={"currency": "EUR"})
    assert (
        _rule_map(policy.evaluate(bad_plan_curr, 5_000_000, "USD", provs, []))[RuleId.CURRENCY_MATCH]
        == RuleOutcome.BLOCK
    )
    # Item currency != goal currency
    bad_item_curr = plan.model_copy(
        update={
            "items": [
                plan.items[0].model_copy(update={"currency": "EUR"}),
                plan.items[1],
            ]
        }
    )
    assert (
        _rule_map(policy.evaluate(bad_item_curr, 5_000_000, "USD", provs, []))[RuleId.CURRENCY_MATCH]
        == RuleOutcome.BLOCK
    )


def test_no_duplicate_pass_and_fail() -> None:
    provs = _providers()
    plan = _clean_plan()
    assert (
        _rule_map(policy.evaluate(plan, 5_000_000, "USD", provs, [PlanStatus.DRAFT, PlanStatus.CHECKED]))[
            RuleId.NO_DUPLICATE
        ]
        == RuleOutcome.PASS
    )
    assert (
        _rule_map(policy.evaluate(plan, 5_000_000, "USD", provs, [PlanStatus.PAYING]))[RuleId.NO_DUPLICATE]
        == RuleOutcome.BLOCK
    )
    assert (
        _rule_map(policy.evaluate(plan, 5_000_000, "USD", provs, [PlanStatus.PAID]))[RuleId.NO_DUPLICATE]
        == RuleOutcome.BLOCK
    )


def test_price_floor_pass_and_fail() -> None:
    provs = _providers()
    plan = _clean_plan()
    # Provider 1 listing price is 2,500,000 (1 pack, no shipping); a lower line price is tampered
    below_floor = PlanDraft(
        items=[
            plan.items[0].model_copy(update={"price_minor": 2_399_999}),
            plan.items[1],
        ],
        total_minor=3_999_999,
        currency="USD",
    )
    assert _rule_map(policy.evaluate(below_floor, 5_000_000, "USD", provs, []))[RuleId.PRICE_FLOOR] == RuleOutcome.BLOCK


def test_total_integrity_pass_and_fail() -> None:
    provs = _providers()
    plan = _clean_plan()
    tampered = plan.model_copy(update={"total_minor": 4_000_000})
    assert (
        _rule_map(policy.evaluate(tampered, 5_000_000, "USD", provs, []))[RuleId.TOTAL_INTEGRITY] == RuleOutcome.BLOCK
    )


def test_single_vendor_share_pass_and_review() -> None:
    provs = _providers()
    # Exact 70% boundary: 2,870,000 / 4,100,000 == 70% -> PASS
    exact_70 = PlanDraft(
        items=[
            PlanItem(
                need_key="catering",
                provider_id=1,
                provider_name="ABC Catering",
                price_minor=2_870_000,
                timeline_days=7,
                verified=True,
                currency="USD",
            ),
            PlanItem(
                need_key="photography",
                provider_id=2,
                provider_name="Studio X",
                price_minor=1_230_000,
                timeline_days=4,
                verified=True,
                currency="USD",
            ),
        ],
        total_minor=4_100_000,
        currency="USD",
    )
    assert (
        _rule_map(policy.evaluate(exact_70, 5_000_000, "USD", provs, []))[RuleId.SINGLE_VENDOR_SHARE]
        == RuleOutcome.PASS
    )

    # Just above 70%: 2,870,001 / 4,100,000 -> REVIEW
    over_70 = PlanDraft(
        items=[
            exact_70.items[0].model_copy(update={"price_minor": 2_870_001}),
            exact_70.items[1].model_copy(update={"price_minor": 1_229_999}),
        ],
        total_minor=4_100_000,
        currency="USD",
    )
    assert (
        _rule_map(policy.evaluate(over_70, 5_000_000, "USD", provs, []))[RuleId.SINGLE_VENDOR_SHARE]
        == RuleOutcome.REVIEW
    )

    # Aggregated per provider_id across multiple items (40% + 40% = 80% > 70%) -> REVIEW
    multi_item_same_vendor = PlanDraft(
        items=[
            PlanItem(
                need_key="lunch",
                provider_id=1,
                provider_name="ABC Catering",
                price_minor=2_000_000,
                timeline_days=7,
                verified=True,
                currency="USD",
            ),
            PlanItem(
                need_key="dinner",
                provider_id=1,
                provider_name="ABC Catering",
                price_minor=2_000_000,
                timeline_days=7,
                verified=True,
                currency="USD",
            ),
            PlanItem(
                need_key="photography",
                provider_id=2,
                provider_name="Studio X",
                price_minor=1_000_000,
                timeline_days=4,
                verified=True,
                currency="USD",
            ),
        ],
        total_minor=5_000_000,
        currency="USD",
    )
    assert (
        _rule_map(policy.evaluate(multi_item_same_vendor, 5_000_000, "USD", provs, []))[RuleId.SINGLE_VENDOR_SHARE]
        == RuleOutcome.REVIEW
    )


def test_risk_assess_success_and_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    plan = _clean_plan()

    def fake_ok(system: str, user: str, schema_model: type, *, task: str) -> RiskLLMOut:
        assert task == "risk"
        return RiskLLMOut(
            risk_score=0.25,
            flags=[RiskFlagLLM(id="tight_timeline", message="Event is in 10 days")],
        )

    monkeypatch.setattr(llm, "call_json", fake_ok)
    score, flags, ai_ok = risk.assess(plan, "Corporate event", 5_000_000)
    assert ai_ok is True
    assert score == 0.25
    assert len(flags) == 1
    assert flags[0] == Flag(
        id="AI:tight_timeline",
        source="AI",
        message="Event is in 10 days",
        requires_ack=False,
    )

    def fake_fail(system: str, user: str, schema_model: type, *, task: str) -> RiskLLMOut:
        raise llm.LLMFailure("simulated timeout")

    monkeypatch.setattr(llm, "call_json", fake_fail)
    score2, flags2, ai_ok2 = risk.assess(plan, "Corporate event", 5_000_000)
    assert (score2, flags2, ai_ok2) == (None, [], False)


def test_engine_combine_ordering_and_thresholds() -> None:
    pol = policy.evaluate(_clean_plan(), 5_000_000, "USD", _providers(), [])

    # Low risk -> APPROVED, 10 rules in RuleId order
    res_low = engine.combine(pol, 0.1, [Flag(id="AI:note", source="AI", message="looks good")], True)
    assert res_low.verdict == Verdict.APPROVED
    assert res_low.ai_ok is True
    assert [r.id for r in res_low.rules] == [rid.value for rid in RuleId]
    assert [f.id for f in res_low.flags] == ["AI:note"]
    assert res_low.flags[0].requires_ack is False

    # Medium risk (0.4 <= score < 0.7) -> REVIEW
    res_med = engine.combine(pol, 0.45, [], True)
    assert res_med.verdict == Verdict.REVIEW
    rmap_med = _rule_map(res_med.rules)
    assert rmap_med[RuleId.AI_RISK_HIGH] == RuleOutcome.PASS
    assert rmap_med[RuleId.AI_RISK_MEDIUM] == RuleOutcome.REVIEW
    assert any(f.id == RuleId.AI_RISK_MEDIUM and f.requires_ack for f in res_med.flags)

    # High risk (score >= 0.7) -> BLOCKED
    res_high = engine.combine(pol, 0.75, [], True)
    assert res_high.verdict == Verdict.BLOCKED
    rmap_high = _rule_map(res_high.rules)
    assert rmap_high[RuleId.AI_RISK_HIGH] == RuleOutcome.BLOCK
    assert rmap_high[RuleId.AI_RISK_MEDIUM] == RuleOutcome.REVIEW


def test_ai_failure_caps_verdict_at_review() -> None:
    pol = policy.evaluate(_clean_plan(), 5_000_000, "USD", _providers(), [])
    res = engine.combine(pol, None, [], False)
    assert res.ai_ok is False
    assert res.verdict == Verdict.REVIEW
    by_id = {r.id: r for r in res.rules}
    assert by_id[RuleId.AI_RISK_HIGH].result == RuleOutcome.REVIEW
    assert by_id[RuleId.AI_RISK_HIGH].detail == "AI risk check unavailable"
    assert by_id[RuleId.AI_RISK_MEDIUM].result == RuleOutcome.REVIEW
    assert by_id[RuleId.AI_RISK_MEDIUM].detail == "AI risk check unavailable"
    ack_ids = {f.id for f in res.flags if f.requires_ack}
    assert ack_ids == {RuleId.AI_RISK_HIGH.value, RuleId.AI_RISK_MEDIUM.value}


def test_ai_cannot_override_policy_block() -> None:
    # Over-budget plan causes BUDGET_CAP == BLOCK
    pol = policy.evaluate(_clean_plan(), 1_000_000, "USD", _providers(), [])
    # Even with risk_score = 0.0 and ai_ok = True, verdict is BLOCKED
    res_ok = engine.combine(pol, 0.0, [], True)
    assert res_ok.verdict == Verdict.BLOCKED
    # Even when AI fails (ai_ok = False), verdict remains BLOCKED (not downgraded to REVIEW)
    res_fail = engine.combine(pol, None, [], False)
    assert res_fail.verdict == Verdict.BLOCKED


def test_run_for_plan_detects_tampered_total_and_duplicate() -> None:
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    SessionMaker = sessionmaker(bind=eng, expire_on_commit=False)

    with SessionMaker() as s:  # type: ignore[misc]
        assert isinstance(s, Session)
        p1 = Provider(
            id=1,
            name="ABC Catering",
            category="catering",
            base_price_minor=2_500_000,
            min_price_minor=2_500_000,
            concession_rate=0.0375,
            rating=4.6,
            turnaround_days=7,
            verified=True,
            currency="USD",
        )
        p2 = Provider(
            id=2,
            name="Studio X",
            category="photography",
            base_price_minor=1_600_000,
            min_price_minor=1_600_000,
            concession_rate=0.0385,
            rating=4.7,
            turnaround_days=4,
            verified=True,
            currency="USD",
        )
        goal = Goal(
            id=10,
            raw_text="Corporate event catering and photography",
            budget_minor=5_000_000,
            currency="USD",
            status="PLAN_READY",
        )
        items_json = [i.model_dump() for i in _clean_plan().items]
        clean_plan_row = Plan(
            id=100,
            goal_id=10,
            items=items_json,
            total_minor=4_100_000,
            currency="USD",
            rationale="Clean plan",
            status=PlanStatus.CHECKED,
        )
        tampered_plan_row = Plan(
            id=101,
            goal_id=10,
            items=items_json,
            total_minor=1_000,  # tampered stored total != sum(items)
            currency="USD",
            rationale="Tampered plan",
            status=PlanStatus.CHECKED,
        )
        s.add_all([p1, p2, goal, clean_plan_row, tampered_plan_row])
        s.commit()

        res_clean = engine.run_for_plan(s, 100)
        assert res_clean.verdict == Verdict.APPROVED

        res_tampered = engine.run_for_plan(s, 101)
        assert res_tampered.verdict == Verdict.BLOCKED
        assert _rule_map(res_tampered.rules)[RuleId.TOTAL_INTEGRITY] == RuleOutcome.BLOCK

        # Mark plan 101 as PAYING -> plan 100 must now fail NO_DUPLICATE
        tampered_plan_row.status = PlanStatus.PAYING
        s.commit()
        res_dup = engine.run_for_plan(s, 100)
        assert res_dup.verdict == Verdict.BLOCKED
        assert _rule_map(res_dup.rules)[RuleId.NO_DUPLICATE] == RuleOutcome.BLOCK

        with pytest.raises(ApiError) as exc_info:
            engine.run_for_plan(s, 9999)
        assert exc_info.value.code == ErrorCode.NOT_FOUND

    eng.dispose()
