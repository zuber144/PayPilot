"""Cart Optimizer (Planning Agent): selects the cheapest within-budget cart, one listing per item.

Pure function: code computes all totals and rankings; LLM writes only the plain-language rationale.
"""

import itertools
import json

from app.config import settings
from app.enums import OfferStatus
from app.llm import LLMFailure, call_json
from app.schemas import Need, OfferDraft, PlanDraft, PlanItem, ProviderOut, RationaleLLMOut

_SYSTEM_PROMPT = (
    "You are the Cart Optimizer for PayPal AgentOS. "
    "Write a concise rationale explaining why the selected store listings form the best cart "
    "for the shopping list based on total cost, seller ratings, and delivery time. "
    "Do not invent or modify any prices or totals."
)


def _latest_offers_for_need(
    final_offers: list[OfferDraft],
    need_key: str,
    providers: dict[int, ProviderOut],
) -> list[OfferDraft]:
    """Select the latest-round non-rejected offer per provider for a given need_key."""
    by_provider: dict[int, OfferDraft] = {}
    for offer in final_offers:
        if offer.need_key != need_key:
            continue
        if offer.status == OfferStatus.REJECTED:
            continue
        if offer.provider_id not in providers:
            continue
        existing = by_provider.get(offer.provider_id)
        if existing is None or (offer.round, -offer.price_minor) > (
            existing.round,
            -existing.price_minor,
        ):
            by_provider[offer.provider_id] = offer
    return list(by_provider.values())


def _fmt(minor: int) -> str:
    """Integer minor units -> '1,234.56' (display only; no float arithmetic)."""
    return f"{minor // 100:,}.{minor % 100:02d}"


def _template_rationale(items: list[PlanItem], total_minor: int, budget_minor: int, currency: str) -> str:
    chosen = "; ".join(
        f"{item.need_key}: {item.packs} x {item.product_title or item.provider_name} from "
        f"{item.provider_name} for {currency} {_fmt(item.price_minor)}"
        + (f" ({item.original_currency} {_fmt(item.original_price_minor)})" if item.original_price_minor else "")
        for item in items
    )
    return (
        f"Cart: {chosen}. Total {currency} {_fmt(total_minor)} within the "
        f"{currency} {_fmt(budget_minor)} budget, choosing the lowest total including shipping, "
        f"then seller rating and delivery time."
    )


def _plan_item(offer: OfferDraft, provider: ProviderOut, currency: str) -> PlanItem:
    packs = max(1, int(offer.packs))
    return PlanItem(
        need_key=offer.need_key,
        provider_id=offer.provider_id,
        provider_name=provider.name,
        price_minor=int(offer.price_minor),
        timeline_days=int(offer.timeline_days),
        verified=provider.verified,
        currency=provider.currency or currency,
        store=provider.store,
        product_title=provider.product_title,
        url=provider.url,
        quantity=offer.quantity,
        packs=packs,
        pack_price_minor=int(provider.base_price_minor),
        shipping_minor=int(provider.shipping_minor),
        original_currency=provider.original_currency,
        original_price_minor=packs * int(provider.original_price_minor) + int(provider.original_shipping_minor),
    )


def run(
    final_offers: list[OfferDraft],
    needs: list[Need],
    providers: dict[int, ProviderOut],
    budget_minor: int,
    currency: str,
) -> tuple[PlanDraft | None, bool]:
    """Pick the best combination of offers (one per need) within budget_minor."""
    if not needs or not final_offers:
        return None, False

    offers_per_need: list[list[OfferDraft]] = []
    for need in needs:
        need_offers = _latest_offers_for_need(final_offers, need.key, providers)
        if not need_offers:
            return None, False
        offers_per_need.append(need_offers)

    combos = itertools.islice(
        itertools.product(*offers_per_need),
        settings.MAX_PLAN_COMBINATIONS,
    )

    best_combo: tuple[OfferDraft, ...] | None = None
    best_key: tuple[int, float, int, tuple[int, ...]] | None = None

    for combo in combos:
        total_minor = sum(int(o.price_minor) for o in combo)
        if total_minor > budget_minor:
            continue
        avg_rating = sum(providers[o.provider_id].rating for o in combo) / len(combo)
        max_turnaround = max(int(o.timeline_days) for o in combo)
        provider_ids = tuple(o.provider_id for o in combo)
        sort_key = (total_minor, -avg_rating, max_turnaround, provider_ids)
        if best_key is None or sort_key < best_key:
            best_key = sort_key
            best_combo = combo

    if best_combo is None or best_key is None:
        return None, False

    best_total = best_key[0]
    items = [_plan_item(offer, providers[offer.provider_id], currency) for offer in best_combo]

    fallback_used = False
    user_payload = json.dumps(
        {
            "currency": currency,
            "items": [
                {
                    "need_key": item.need_key,
                    "provider_name": item.provider_name,
                    "store": item.store,
                    "packs": item.packs,
                    "timeline_days": item.timeline_days,
                    "verified": item.verified,
                }
                for item in items
            ],
        }
    )
    try:
        llm_out = call_json(
            _SYSTEM_PROMPT,
            user_payload,
            RationaleLLMOut,
            task="plan_rationale",
        )
        rationale = llm_out.rationale.strip()
        if not rationale:
            rationale = _template_rationale(items, best_total, budget_minor, currency)
    except LLMFailure:
        fallback_used = True
        rationale = _template_rationale(items, best_total, budget_minor, currency)

    return (
        PlanDraft(
            items=items,
            total_minor=best_total,
            currency=currency,
            rationale=rationale,
        ),
        fallback_used,
    )
