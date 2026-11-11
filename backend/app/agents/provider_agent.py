"""Product Extractor Agent: turns candidate store listings into round-0 product offers.

Quantities and prices are computed in code from the listing record:
packs = ceil(quantity / pack_size), line total = packs * pack price + shipping (USD cents).
The LLM writes only the short product summary text; on LLMFailure a template string is used.
"""

import json

from app.enums import OfferStatus
from app.llm import LLMFailure, call_json
from app.schemas import Need, OfferDraft, OfferTextLLMOut, ProviderOut

_SYSTEM_PROMPT = (
    "You are the Product Extractor Agent. Write a one-sentence summary of the store listing for the "
    "shopper's item (what is in the pack, store, delivery). Do not mention, invent or alter prices."
)


def packs_needed(quantity: int | None, pack_size: int) -> int:
    """Packs to buy so that packs * pack_size >= quantity (integer ceil). None/0 quantity = 1 pack."""
    size = max(1, int(pack_size))
    if not quantity or quantity <= 0:
        return 1
    return -(-int(quantity) // size)


def line_total_minor(packs: int, provider: ProviderOut) -> int:
    return packs * int(provider.base_price_minor) + int(provider.shipping_minor)


def _template_scope(need: Need, provider: ProviderOut, packs: int) -> str:
    title = provider.product_title or provider.name
    store = provider.store.capitalize() if provider.store else provider.name
    units = packs * max(1, provider.pack_size)
    return f"{packs} x {title} on {store} ({units} units), delivery in {provider.turnaround_days} days."


def run(need: Need, providers: list[ProviderOut]) -> tuple[list[OfferDraft], bool]:
    """Create round-0 offers (one per listing) for a shopping-list item."""
    offers: list[OfferDraft] = []
    fallback_used = False

    for provider in providers:
        packs = packs_needed(need.quantity, provider.pack_size)
        user_payload = json.dumps(
            {
                "need_key": need.key,
                "category": need.category,
                "quantity": need.quantity,
                "must_haves": need.must_haves,
                "provider_id": provider.id,
                "provider_name": provider.name,
                "store": provider.store,
                "product_title": provider.product_title[:200],  # untrusted page text, truncated
                "pack_size": provider.pack_size,
                "packs": packs,
                "turnaround_days": provider.turnaround_days,
            }
        )
        try:
            text_out = call_json(_SYSTEM_PROMPT, user_payload, OfferTextLLMOut, task="offer_text")
            scope = text_out.scope.strip()
            if text_out.pitch.strip():
                scope = f"{scope} — {text_out.pitch.strip()}" if scope else text_out.pitch.strip()
            if not scope:
                scope = _template_scope(need, provider, packs)
        except LLMFailure:
            fallback_used = True
            scope = _template_scope(need, provider, packs)

        offers.append(
            OfferDraft(
                need_key=need.key,
                provider_id=provider.id,
                round=0,
                price_minor=line_total_minor(packs, provider),
                counter_minor=None,
                timeline_days=provider.turnaround_days,
                scope=scope[:1000],
                status=OfferStatus.OPEN,
                quantity=need.quantity,
                packs=packs,
                pack_price_minor=int(provider.base_price_minor),
                shipping_minor=int(provider.shipping_minor),
            )
        )

    return offers, fallback_used
