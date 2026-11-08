"""
app/agents/negotiation.py — Step 4: multi-round offer negotiation.

Rules:
- Up to 2 counter rounds.
- Buyer counters at 85% of previous price (round 1) then 92% (round 2).
- Provider accepts if the counter >= their min_price_minor.
- Price NEVER goes below min_price_minor.
"""
from __future__ import annotations

from app.schemas import NegotiatedOffer, ProviderOffer, ProviderOut

_COUNTER_RATES = [0.85, 0.92]  # buyer counter as fraction of previous price
MAX_ROUNDS = 2


def negotiate(
    offer: ProviderOffer,
    provider: ProviderOut,
) -> NegotiatedOffer:
    """
    Run up to MAX_ROUNDS of negotiation.
    Returns the final agreed price and whether the provider accepted.
    """
    current_price = offer.price_minor
    rounds_done = 0
    accepted = False

    for i, rate in enumerate(_COUNTER_RATES):
        counter_price = int(current_price * rate)
        # Price floor: never go below min_price_minor
        counter_price = max(counter_price, provider.min_price_minor)
        rounds_done = i + 1

        if counter_price >= provider.min_price_minor:
            # Provider accepts — deal done at counter price
            current_price = counter_price
            accepted = True
            break
        else:
            # Provider rejects, holds at min_price
            current_price = provider.min_price_minor
            accepted = True  # Accept at floor
            break

    if not accepted:
        # After all rounds, accept at min_price if buyer's last counter >= floor
        current_price = max(current_price, provider.min_price_minor)
        accepted = True

    return NegotiatedOffer(
        provider_id=provider.id,
        need_key=offer.need_key,
        final_price_minor=current_price,
        rounds=rounds_done,
        accepted=accepted,
        scope=offer.scope,
        timeline_days=offer.timeline_days,
    )


def negotiate_all(
    offers: list[ProviderOffer],
    providers_by_id: dict[int, ProviderOut],
) -> list[NegotiatedOffer]:
    """Negotiate all offers and return results."""
    return [negotiate(o, providers_by_id[o.provider_id]) for o in offers]
