"""Tests for negotiation pricing boundaries and floor enforcement."""

import pytest

from app.agents import negotiation_agent
from app.config import settings
from app.enums import OfferStatus, RuleId, RuleOutcome
from app.payguard import policy
from app.schemas import OfferDraft, PlanDraft, PlanItem, ProviderOut


@pytest.mark.parametrize("concession_rate", [0.01, 0.05, 0.15, 0.30, 0.50, 0.90])
def test_price_never_below_provider_minimum_across_rounds(concession_rate: float) -> None:
    """Section 15 #5: Price below provider minimum —
    Negotiation and pricing constraints are enforced by code (never below min_price_minor).
    """
    provider = ProviderOut(
        id=1,
        name="Test Catering",
        category="catering",
        base_price_minor=2_800_000,
        min_price_minor=2_400_000,
        concession_rate=concession_rate,
        rating=4.6,
        turnaround_days=7,
        verified=True,
        currency="INR",
    )
    providers = {1: provider}
    offers = [
        OfferDraft(
            need_key="catering",
            provider_id=1,
            round=0,
            price_minor=provider.base_price_minor,
            timeline_days=provider.turnaround_days,
            status=OfferStatus.OPEN,
        )
    ]

    for round_no in range(1, settings.MAX_NEGOTIATION_ROUNDS + 1):
        offers = negotiation_agent.run_round(offers, providers, round_no=round_no)
        assert len(offers) == 1
        assert isinstance(offers[0].price_minor, int)
        assert offers[0].price_minor >= provider.min_price_minor

    # Rounds beyond MAX_NEGOTIATION_ROUNDS are rejected by the hard bound
    with pytest.raises(ValueError):
        negotiation_agent.run_round(offers, providers, round_no=settings.MAX_NEGOTIATION_ROUNDS + 1)


def test_accepted_offers_carry_over_unchanged() -> None:
    """Once an offer reaches ACCEPTED, subsequent rounds keep it unchanged at >= min_price_minor."""
    provider = ProviderOut(
        id=2,
        name="Studio X",
        category="photography",
        base_price_minor=1_800_000,
        min_price_minor=1_500_000,
        concession_rate=0.25,
        rating=4.7,
        turnaround_days=4,
        verified=True,
        currency="INR",
    )
    providers = {2: provider}
    offers = [
        OfferDraft(
            need_key="photography",
            provider_id=2,
            round=1,
            price_minor=1_600_000,
            counter_minor=1_600_000,
            timeline_days=4,
            status=OfferStatus.ACCEPTED,
        )
    ]

    next_offers = negotiation_agent.run_round(offers, providers, round_no=2)
    assert next_offers[0].status == OfferStatus.ACCEPTED
    assert next_offers[0].price_minor == 1_600_000
    assert next_offers[0].price_minor >= provider.min_price_minor


def test_price_floor_blocks_tampered_plan() -> None:
    """Section 15 #5 (policy): PRICE_FLOOR blocks a plan whose item price is below min_price_minor."""
    provider = ProviderOut(
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
    )
    tampered_plan = PlanDraft(
        items=[
            PlanItem(
                need_key="catering",
                provider_id=1,
                provider_name="ABC Catering",
                price_minor=2_399_999,
                timeline_days=7,
                verified=True,
                currency="INR",
            )
        ],
        total_minor=2_399_999,
        currency="INR",
        rationale="Tampered below floor",
    )
    results = policy.evaluate(
        plan=tampered_plan,
        goal_budget_minor=5_000_000,
        goal_currency="INR",
        providers={1: provider},
        other_plan_statuses=[],
    )
    by_id = {r.id: r for r in results}
    assert by_id[RuleId.PRICE_FLOOR].result == RuleOutcome.BLOCK
