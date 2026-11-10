"""Negotiation Agent: deterministic integer price negotiation bounded by MAX_NEGOTIATION_ROUNDS.

Pure function: no DB writes, no trace writes.
Prices never go below provider.min_price_minor.
"""

from app.config import settings
from app.enums import OfferStatus
from app.schemas import OfferDraft, ProviderOut


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
) -> list[OfferDraft]:
    """Run one bounded negotiation round using exact integer arithmetic."""
    if round_no < 1 or round_no > settings.MAX_NEGOTIATION_ROUNDS:
        raise ValueError(
            f"round_no must be between 1 and {settings.MAX_NEGOTIATION_ROUNDS}, got {round_no}"
        )

    result: list[OfferDraft] = []
    for offer in _latest_offers(offers):
        if offer.status == OfferStatus.REJECTED:
            continue

        provider = providers[offer.provider_id]
        min_price = int(provider.min_price_minor)

        if offer.status == OfferStatus.ACCEPTED:
            result.append(
                OfferDraft(
                    need_key=offer.need_key,
                    provider_id=offer.provider_id,
                    round=round_no,
                    price_minor=max(int(offer.price_minor), min_price),
                    counter_minor=offer.counter_minor,
                    timeline_days=offer.timeline_days,
                    scope=offer.scope,
                    status=OfferStatus.ACCEPTED,
                )
            )
            continue

        price = int(offer.price_minor)
        counter = int(price * settings.COUNTER_RATIO)
        new_price = max(min_price, round(price * (1 - provider.concession_rate)))

        if new_price <= counter:
            final_price = max(counter, min_price)
            status = OfferStatus.ACCEPTED
        else:
            final_price = max(new_price, min_price)
            status = OfferStatus.COUNTERED

        result.append(
            OfferDraft(
                need_key=offer.need_key,
                provider_id=offer.provider_id,
                round=round_no,
                price_minor=final_price,
                counter_minor=counter,
                timeline_days=offer.timeline_days,
                scope=offer.scope,
                status=status,
            )
        )

    return result
