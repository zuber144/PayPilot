"""Focused unit tests for negotiation_agent."""

import pytest

from app.agents import negotiation_agent
from app.enums import OfferStatus
from app.schemas import OfferDraft, ProviderOut


def _make_provider(
    pid: int,
    name: str,
    base_minor: int,
    min_minor: int,
    rate: float,
    *,
    category: str = "catering",
    rating: float = 4.5,
    turnaround: int = 5,
    verified: bool = True,
) -> ProviderOut:
    return ProviderOut(
        id=pid,
        name=name,
        category=category,
        base_price_minor=base_minor,
        min_price_minor=min_minor,
        concession_rate=rate,
        rating=rating,
        turnaround_days=turnaround,
        verified=verified,
        currency="USD",
    )


def test_clean_scenario_three_rounds_exact_math() -> None:
    abc = _make_provider(1, "ABC Catering", 2_800_000, 2_400_000, 0.0375)
    studio_x = _make_provider(
        2, "Studio X", 1_800_000, 1_500_000, 0.0385, category="photography"
    )
    providers = {1: abc, 2: studio_x}

    offers = [
        OfferDraft(
            need_key="catering",
            provider_id=1,
            round=0,
            price_minor=abc.base_price_minor,
            timeline_days=7,
            status=OfferStatus.OPEN,
        ),
        OfferDraft(
            need_key="photography",
            provider_id=2,
            round=0,
            price_minor=studio_x.base_price_minor,
            timeline_days=4,
            status=OfferStatus.OPEN,
        ),
    ]

    for r in (1, 2, 3):
        offers = negotiation_agent.run_round(offers, providers, r)

    by_pid = {o.provider_id: o for o in offers}
    # ABC: 28,000 -> ~24,966.65 (2,496,665 cents)
    assert by_pid[1].price_minor == 2_496_665
    assert by_pid[1].round == 3
    assert by_pid[1].status == OfferStatus.COUNTERED
    # Studio X: 18,000 -> ~16,000.01 (1,600,001 cents)
    assert by_pid[2].price_minor == 1_600_001
    assert by_pid[2].round == 3
    assert by_pid[2].status == OfferStatus.COUNTERED


def test_price_never_below_min_price_minor() -> None:
    prov = _make_provider(1, "Floor Provider", 2_100_000, 2_000_000, 0.25)
    providers = {1: prov}
    offers = [
        OfferDraft(
            need_key="catering",
            provider_id=1,
            round=0,
            price_minor=prov.base_price_minor,
            timeline_days=5,
            status=OfferStatus.OPEN,
        )
    ]

    for r in (1, 2, 3):
        offers = negotiation_agent.run_round(offers, providers, r)
        assert offers[0].price_minor >= prov.min_price_minor


def test_accepted_offer_carries_over_unchanged() -> None:
    prov = _make_provider(1, "Generous Provider", 2_000_000, 1_500_000, 0.12)
    providers = {1: prov}
    offers = [
        OfferDraft(
            need_key="catering",
            provider_id=1,
            round=0,
            price_minor=2_000_000,
            timeline_days=5,
            status=OfferStatus.OPEN,
        )
    ]

    r1 = negotiation_agent.run_round(offers, providers, 1)
    assert r1[0].status == OfferStatus.ACCEPTED
    accepted_price = r1[0].price_minor
    assert accepted_price == 1_800_000  # counter = 90% of 2,000,000

    r2 = negotiation_agent.run_round(r1, providers, 2)
    assert r2[0].status == OfferStatus.ACCEPTED
    assert r2[0].price_minor == accepted_price
    assert r2[0].round == 2


def test_round_bounds_enforced() -> None:
    prov = _make_provider(1, "ABC", 2_800_000, 2_400_000, 0.0375)
    offers = [
        OfferDraft(
            need_key="catering",
            provider_id=1,
            round=0,
            price_minor=2_800_000,
            timeline_days=7,
            status=OfferStatus.OPEN,
        )
    ]
    with pytest.raises(ValueError):
        negotiation_agent.run_round(offers, {1: prov}, 0)
    with pytest.raises(ValueError):
        negotiation_agent.run_round(offers, {1: prov}, 4)
