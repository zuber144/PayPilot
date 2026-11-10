"""Provider Agent: builds round-0 opening offers for candidate providers.

Prices and timelines come strictly from the provider record.
The LLM writes only the scope/pitch text; on LLMFailure a template string is used.
"""

import json

from app.enums import OfferStatus
from app.llm import LLMFailure, call_json
from app.schemas import Need, OfferDraft, OfferTextLLMOut, ProviderOut

_SYSTEM_PROMPT = (
    "You are a Provider Offer Agent. Write a concise service scope and short pitch "
    "for the provider's opening offer matching the customer's need. "
    "Do not invent or alter prices."
)


def _template_scope(need: Need, provider: ProviderOut) -> str:
    qty_part = f" for {need.quantity}" if need.quantity else ""
    must_part = f" ({', '.join(need.must_haves)})" if need.must_haves else ""
    return (
        f"{provider.name} {need.category} service{qty_part}{must_part}, "
        f"delivered in {provider.turnaround_days} days."
    )


def run(need: Need, providers: list[ProviderOut]) -> tuple[list[OfferDraft], bool]:
    """Create round-0 opening offers for each provider candidate."""
    offers: list[OfferDraft] = []
    fallback_used = False

    for provider in providers:
        user_payload = json.dumps(
            {
                "need_key": need.key,
                "category": need.category,
                "quantity": need.quantity,
                "must_haves": need.must_haves,
                "provider_id": provider.id,
                "provider_name": provider.name,
                "turnaround_days": provider.turnaround_days,
                "persona": provider.persona,
            }
        )
        try:
            text_out = call_json(
                _SYSTEM_PROMPT,
                user_payload,
                OfferTextLLMOut,
                task="offer_text",
            )
            scope = text_out.scope.strip()
            if text_out.pitch.strip():
                scope = f"{scope} — {text_out.pitch.strip()}" if scope else text_out.pitch.strip()
            if not scope:
                scope = _template_scope(need, provider)
        except LLMFailure:
            fallback_used = True
            scope = _template_scope(need, provider)

        offers.append(
            OfferDraft(
                need_key=need.key,
                provider_id=provider.id,
                round=0,
                price_minor=provider.base_price_minor,
                counter_minor=None,
                timeline_days=provider.turnaround_days,
                scope=scope,
                status=OfferStatus.OPEN,
            )
        )

    return offers, fallback_used
