"""Planning Agent: selects the optimal within-budget combination of offers across needs.

Pure function: code computes all totals and rankings; LLM writes only the plain-language rationale.
"""

import itertools
import json

from app.config import settings
from app.enums import OfferStatus
from app.llm import LLMFailure, call_json
from app.schemas import Need, OfferDraft, PlanDraft, PlanItem, ProviderOut, RationaleLLMOut

_SYSTEM_PROMPT = (
    "You are the Planning Agent for PayPal AgentOS. "
    "Write a concise rationale explaining why the selected providers form the best plan "
    "for the user's needs based on cost efficiency, ratings, and delivery timeline. "
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


def _template_rationale(items: list[PlanItem], total_minor: int, budget_minor: int, currency: str) -> str:
    chosen = ", ".join(f"{item.provider_name} for {item.need_key}" for item in items)
    total_major = total_minor // 100
    budget_major = budget_minor // 100
    return (
        f"Selected {chosen} at {currency} {total_major:,} within the "
        f"{currency} {budget_major:,} budget, balancing lowest negotiated total, "
        f"provider ratings, and delivery turnaround."
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
    items = [
        PlanItem(
            need_key=offer.need_key,
            provider_id=offer.provider_id,
            provider_name=providers[offer.provider_id].name,
            price_minor=int(offer.price_minor),
            timeline_days=int(offer.timeline_days),
            verified=providers[offer.provider_id].verified,
            currency=providers[offer.provider_id].currency or currency,
        )
        for offer in best_combo
    ]

    fallback_used = False
    user_payload = json.dumps(
        {
            "currency": currency,
            "items": [
                {
                    "need_key": item.need_key,
                    "provider_name": item.provider_name,
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
