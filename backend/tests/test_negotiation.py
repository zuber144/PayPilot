"""Section 15 #5: pricing constraints enforced by code (price comparison + PRICE_FLOOR integrity).

Store prices are fixed: the comparison agent re-derives every line total from the listing record
(packs * pack price + shipping), so a line can never differ from (or drop below) the listing.
"""

import pytest

from app.agents import negotiation_agent
from app.config import settings
from app.enums import OfferStatus, RuleId, RuleOutcome
from app.payguard import policy
from app.schemas import OfferDraft, PlanDraft, PlanItem, ProviderOut


def _listing(pid: int = 1, *, pack_price: int = 298, shipping: int = 48, pack_size: int = 10) -> ProviderOut:
    return ProviderOut(
        id=pid,
        name="PartyZone Official (Flipkart)",
        category="party_hats",
        base_price_minor=pack_price,
        min_price_minor=pack_price,
        rating=4.2,
        turnaround_days=4,
        verified=True,
        currency="USD",
        store="flipkart",
        pack_size=pack_size,
        shipping_minor=shipping,
    )


@pytest.mark.parametrize("tampered_price", [1, 100, 345, 347, 10_000])
def test_comparison_restores_listing_price_whatever_the_incoming_offer_says(tampered_price: int) -> None:
    """Section 15 #5: price below (or above) the listing is never carried into the compared offer."""
    provider = _listing()
    offers = [
        OfferDraft(
            need_key="party_hats",
            provider_id=1,
            round=0,
            price_minor=tampered_price,
            timeline_days=1,
            quantity=10,
            packs=1,
        )
    ]
    for round_no in range(1, settings.MAX_NEGOTIATION_ROUNDS + 1):
        offers = negotiation_agent.run_round(offers, {1: provider}, round_no=round_no)
        assert len(offers) == 1
        assert isinstance(offers[0].price_minor, int)
        assert offers[0].price_minor == 1 * 298 + 48
        assert offers[0].price_minor >= provider.min_price_minor
        assert offers[0].timeline_days == provider.turnaround_days

    # Rounds beyond MAX_NEGOTIATION_ROUNDS are rejected by the hard bound
    with pytest.raises(ValueError):
        negotiation_agent.run_round(offers, {1: provider}, round_no=settings.MAX_NEGOTIATION_ROUNDS + 1)


def test_comparison_recomputes_packs_from_quantity() -> None:
    provider = _listing(pack_size=10)
    offers = [
        OfferDraft(need_key="party_hats", provider_id=1, round=0, price_minor=1, timeline_days=4, quantity=25, packs=1)
    ]
    out = negotiation_agent.run_round(offers, {1: provider}, 1)
    assert out[0].packs == 3
    assert out[0].price_minor == 3 * 298 + 48
    assert out[0].pack_price_minor == 298
    assert out[0].shipping_minor == 48


def _plan(price: int, packs: int = 1) -> PlanDraft:
    return PlanDraft(
        items=[
            PlanItem(
                need_key="party_hats",
                provider_id=1,
                provider_name="PartyZone Official (Flipkart)",
                price_minor=price,
                timeline_days=4,
                verified=True,
                currency="USD",
                packs=packs,
            )
        ],
        total_minor=price,
        currency="USD",
        rationale="",
    )


def _price_floor(plan: PlanDraft) -> RuleOutcome:
    results = policy.evaluate(
        plan=plan, goal_budget_minor=2_000, goal_currency="USD", providers={1: _listing()}, other_plan_statuses=[]
    )
    return {r.id: r for r in results}[RuleId.PRICE_FLOOR].result


def test_price_floor_blocks_tampered_plan() -> None:
    """Section 15 #5 (policy): PRICE_FLOOR blocks any line that differs from packs x listing + shipping."""
    assert _price_floor(_plan(346)) == RuleOutcome.PASS
    assert _price_floor(_plan(345)) == RuleOutcome.BLOCK  # below listing
    assert _price_floor(_plan(298)) == RuleOutcome.BLOCK  # shipping dropped
    assert _price_floor(_plan(2 * 298 + 48, packs=2)) == RuleOutcome.PASS
    assert _price_floor(_plan(346, packs=0)) == RuleOutcome.BLOCK


def test_comparison_offers_are_accepted_and_unknown_status_rejected_dropped() -> None:
    provider = _listing()
    offers = [
        OfferDraft(need_key="party_hats", provider_id=1, round=0, price_minor=346, timeline_days=4, quantity=10),
        OfferDraft(
            need_key="balloons", provider_id=1, round=0, price_minor=346, timeline_days=4, status=OfferStatus.REJECTED
        ),
    ]
    out = negotiation_agent.run_round(offers, {1: provider}, 1)
    assert [o.need_key for o in out] == ["party_hats"]
    assert out[0].status == OfferStatus.ACCEPTED
    assert out[0].counter_minor is None
