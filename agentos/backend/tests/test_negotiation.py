"""
tests/test_negotiation.py — negotiation invariant tests.

Tests:
1. Price never goes below min_price_minor.
2. Negotiation stops at MAX_ROUNDS (2).
3. Provider always accepts at or above min_price.
"""
from __future__ import annotations

import pytest

from app.agents.negotiation import MAX_ROUNDS, negotiate
from app.schemas import ProviderOffer, ProviderOut


def _provider(min_price: int, base_price: int) -> ProviderOut:
    return ProviderOut(
        id=1,
        name="Test Provider",
        category="web_design",
        base_price_minor=base_price,
        min_price_minor=min_price,
        concession_rate=0.15,
        rating=4.5,
        turnaround_days=7,
        verified=True,
        persona="",
    )


def _offer(provider_id: int, need_key: str, price: int) -> ProviderOffer:
    return ProviderOffer(
        provider_id=provider_id,
        need_key=need_key,
        price_minor=price,
        scope="Full service",
        timeline_days=7,
        pitch="We are great.",
    )


def test_price_never_below_min_price():
    """Final price must never be below the provider's min_price_minor."""
    provider = _provider(min_price=30000, base_price=50000)
    offer = _offer(provider.id, "web_design", price=50000)

    result = negotiate(offer, provider)
    assert result.final_price_minor >= provider.min_price_minor, (
        f"Price {result.final_price_minor} went below floor {provider.min_price_minor}"
    )


def test_price_never_below_min_price_aggressive_counter():
    """Even if the buyer's counter would go below floor, floor is respected."""
    provider = _provider(min_price=45000, base_price=50000)
    # Opening at 50000; 85% = 42500 < floor=45000
    offer = _offer(provider.id, "web_design", price=50000)

    result = negotiate(offer, provider)
    assert result.final_price_minor >= provider.min_price_minor


def test_negotiation_stops_at_round_limit():
    """Negotiation must not exceed MAX_ROUNDS rounds."""
    provider = _provider(min_price=10000, base_price=80000)
    offer = _offer(provider.id, "web_design", price=80000)

    result = negotiate(offer, provider)
    assert result.rounds <= MAX_ROUNDS


def test_provider_accepts_at_or_above_min_price():
    """If the counter is at or above min_price, the provider should accept."""
    provider = _provider(min_price=30000, base_price=50000)
    offer = _offer(provider.id, "web_design", price=50000)

    result = negotiate(offer, provider)
    assert result.accepted


def test_final_price_is_less_than_opening():
    """After negotiation, final price should be <= opening price (buyer wins something)."""
    provider = _provider(min_price=20000, base_price=60000)
    offer = _offer(provider.id, "web_design", price=60000)

    result = negotiate(offer, provider)
    assert result.final_price_minor <= offer.price_minor
