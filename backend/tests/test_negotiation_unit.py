"""Focused unit tests for negotiation_agent (the Price Comparison agent)."""

import pytest

from app.agents import negotiation_agent
from app.agents.negotiation_agent import BEST_PRICE, FASTEST_DELIVERY, TOP_RATED
from app.config import settings
from app.enums import OfferStatus
from app.schemas import OfferDraft, ProviderOut


def _listing(
    pid: int,
    pack_price: int,
    *,
    shipping: int = 0,
    pack_size: int = 10,
    rating: float = 4.5,
    days: int = 3,
    category: str = "party_hats",
) -> ProviderOut:
    return ProviderOut(
        id=pid,
        name=f"Seller {pid}",
        category=category,
        base_price_minor=pack_price,
        min_price_minor=pack_price,
        rating=rating,
        turnaround_days=days,
        verified=True,
        currency="USD",
        pack_size=pack_size,
        shipping_minor=shipping,
    )


def _offer(pid: int, need: str = "party_hats", *, rnd: int = 0, qty: int | None = 10, price: int = 1,
           status: OfferStatus = OfferStatus.OPEN) -> OfferDraft:
    return OfferDraft(need_key=need, provider_id=pid, round=rnd, price_minor=price, timeline_days=0,
                      quantity=qty, status=status)


def test_line_totals_and_tags_per_need() -> None:
    # Hats: Flipkart-like 298 + 48 ship (4.2, 4d) vs Amazon-like 358 free (4.4, 2d)
    providers = {
        1: _listing(1, 298, shipping=48, rating=4.2, days=4),
        2: _listing(2, 358, rating=4.4, days=2),
        # Balloons: 237 / pack of 50 (4.5, 1d) vs 143 / pack of 25 (4.3, 3d)
        3: _listing(3, 237, pack_size=50, rating=4.5, days=1, category="balloons"),
        4: _listing(4, 143, pack_size=25, rating=4.3, days=3, category="balloons"),
    }
    offers = [_offer(1), _offer(2), _offer(3, "balloons", qty=50), _offer(4, "balloons", qty=50)]
    out = {o.provider_id: o for o in negotiation_agent.run_round(offers, providers, 1)}

    assert out[1].price_minor == 346
    assert out[2].price_minor == 358
    assert out[3].price_minor == 237
    assert out[4].price_minor == 2 * 143
    assert out[4].packs == 2
    assert all(o.status == OfferStatus.ACCEPTED and o.round == 1 for o in out.values())

    assert out[1].tags == [BEST_PRICE]
    assert sorted(out[2].tags) == sorted([FASTEST_DELIVERY, TOP_RATED])
    assert sorted(out[3].tags) == sorted([BEST_PRICE, FASTEST_DELIVERY, TOP_RATED])
    assert out[4].tags == []


def test_tag_ties_break_deterministically() -> None:
    # Identical price, days and rating -> lowest listing id wins every tag
    providers = {7: _listing(7, 300), 5: _listing(5, 300)}
    out = {o.provider_id: o for o in negotiation_agent.run_round([_offer(7), _offer(5)], providers, 1)}
    assert sorted(out[5].tags) == sorted([BEST_PRICE, FASTEST_DELIVERY, TOP_RATED])
    assert out[7].tags == []

    # Equal price: BEST_PRICE goes to the faster delivery
    providers2 = {1: _listing(1, 300, days=5), 2: _listing(2, 300, days=2)}
    out2 = {o.provider_id: o for o in negotiation_agent.run_round([_offer(1), _offer(2)], providers2, 1)}
    assert BEST_PRICE in out2[2].tags


def test_latest_round_per_pair_is_used_and_rejected_dropped() -> None:
    providers = {1: _listing(1, 298), 2: _listing(2, 358)}
    offers = [
        _offer(1, rnd=0, qty=10),
        _offer(1, rnd=1, qty=30),  # latest round for listing 1 carries quantity 30 -> 3 packs
        _offer(2, rnd=0, status=OfferStatus.REJECTED),
    ]
    out = negotiation_agent.run_round(offers, providers, 1)
    assert [o.provider_id for o in out] == [1]
    assert out[0].packs == 3
    assert out[0].price_minor == 3 * 298


def test_no_quantity_means_one_pack() -> None:
    out = negotiation_agent.run_round([_offer(1, qty=None)], {1: _listing(1, 298, shipping=48)}, 1)
    assert out[0].packs == 1
    assert out[0].price_minor == 346


def test_round_bounds_enforced() -> None:
    providers = {1: _listing(1, 298)}
    offers = [_offer(1)]
    assert settings.MAX_NEGOTIATION_ROUNDS == 1
    with pytest.raises(ValueError):
        negotiation_agent.run_round(offers, providers, 0)
    with pytest.raises(ValueError):
        negotiation_agent.run_round(offers, providers, settings.MAX_NEGOTIATION_ROUNDS + 1)
    # A plan revision allows MAX_PLAN_REVISIONS extra passes
    extra = settings.MAX_NEGOTIATION_ROUNDS + settings.MAX_PLAN_REVISIONS
    out = negotiation_agent.run_round(offers, providers, extra, allow_revision=True)
    assert out[0].round == extra
    with pytest.raises(ValueError):
        negotiation_agent.run_round(offers, providers, extra + 1, allow_revision=True)
