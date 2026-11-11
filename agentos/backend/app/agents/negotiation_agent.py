"""Price Comparison Agent (graph node "negotiation"): store prices are fixed, so instead of
bargaining it re-derives every line total from the listing record and tags the deals per item.

Pure function: no DB writes, no trace writes, integer arithmetic only.
Tags per need: BEST_PRICE (lowest line total incl. shipping), FASTEST_DELIVERY (fewest days),
TOP_RATED (highest seller rating). Ties are broken by listing id so results are deterministic.
"""

from app.agents.provider_agent import line_total_minor, packs_needed
from app.config import settings
from app.enums import OfferStatus
from app.schemas import OfferDraft, ProviderOut

BEST_PRICE = "BEST_PRICE"
FASTEST_DELIVERY = "FASTEST_DELIVERY"
TOP_RATED = "TOP_RATED"


def _latest_offers(offers: list[OfferDraft]) -> list[OfferDraft]:
    """If multiple rounds per (need_key, provider_id) are passed, keep the latest round."""
    latest_by_key: dict[tuple[str, int], OfferDraft] = {}
    order: list[tuple[str, int]] = []
    for offer in offers:
        pair = (offer.need_key, offer.provider_id)
        if pair not in latest_by_key:
            order.append(pair)
            latest_by_key[pair] = offer
        elif offer.round >= latest_by_key[pair].round:
            latest_by_key[pair] = offer
    return [latest_by_key[pair] for pair in order]


def run_round(
    offers: list[OfferDraft],
    providers: dict[int, ProviderOut],
    round_no: int,
    *,
    allow_revision: bool = False,
) -> list[OfferDraft]:
    """Run one bounded comparison pass: recompute line totals and tag the best deals."""
    max_rounds = settings.MAX_NEGOTIATION_ROUNDS + (settings.MAX_PLAN_REVISIONS if allow_revision else 0)
    if round_no < 1 or round_no > max_rounds:
        raise ValueError(f"round_no must be between 1 and {max_rounds}, got {round_no}")

    compared: list[OfferDraft] = []
    for offer in _latest_offers(offers):
        if offer.status == OfferStatus.REJECTED:
            continue
        provider = providers[offer.provider_id]
        packs = packs_needed(offer.quantity, provider.pack_size)
        compared.append(
            OfferDraft(
                need_key=offer.need_key,
                provider_id=offer.provider_id,
                round=round_no,
                price_minor=line_total_minor(packs, provider),
                counter_minor=None,
                timeline_days=provider.turnaround_days,
                scope=offer.scope,
                status=OfferStatus.ACCEPTED,
                quantity=offer.quantity,
                packs=packs,
                pack_price_minor=int(provider.base_price_minor),
                shipping_minor=int(provider.shipping_minor),
                tags=[],
            )
        )

    by_need: dict[str, list[OfferDraft]] = {}
    for off in compared:
        by_need.setdefault(off.need_key, []).append(off)
    for group in by_need.values():
        best = min(group, key=lambda o: (o.price_minor, o.timeline_days, o.provider_id))
        fastest = min(group, key=lambda o: (o.timeline_days, o.price_minor, o.provider_id))
        top = min(group, key=lambda o: (-providers[o.provider_id].rating, o.price_minor, o.provider_id))
        best.tags.append(BEST_PRICE)
        fastest.tags.append(FASTEST_DELIVERY)
        top.tags.append(TOP_RATED)

    return compared
