"""
app/agents/plan_generator.py — Step 5: build the best plan under budget.

Algorithm: brute-force combination of ONE offer per need that maximises:
  score = w1*fit + w2*(1 - price/budget) + w3*speed

Where:
  fit   = provider.rating / 5.0
  speed = 1 - (timeline_days / 60)   (capped at 0)
  w1=0.4, w2=0.35, w3=0.25

The LLM only writes the rationale text (stub returns template).
"""
from __future__ import annotations

import itertools
from typing import Optional

from pydantic import BaseModel

from app.llm import complete_json
from app.schemas import GeneratedPlan, NegotiatedOffer, PlanItem, ProviderOut

W1, W2, W3 = 0.4, 0.35, 0.25


class _RationaleResponse(BaseModel):
    rationale: str


_FALLBACK_RATIONALE = _RationaleResponse(
    rationale=(
        "Selected providers offer the best balance of quality, price, and delivery speed "
        "within your budget. All vendors are verified and highly rated by previous clients."
    )
)


def _score_item(
    offer: NegotiatedOffer,
    provider: ProviderOut,
    budget_minor: int,
) -> float:
    fit = provider.rating / 5.0
    price_ratio = offer.final_price_minor / max(budget_minor, 1)
    speed = max(0.0, 1.0 - offer.timeline_days / 60.0)
    return W1 * fit + W2 * (1 - price_ratio) + W3 * speed


def _get_rationale(items: list[PlanItem]) -> tuple[str, bool]:
    """Ask the LLM for a rationale string (stub returns a template)."""
    # TODO(llm-owner): build a richer prompt with the actual plan items,
    # provider names, prices and explain why this combination was chosen.
    provider_names = ", ".join({i.provider_name for i in items})
    prompt = (
        f"rationale\n"
        f"Write a 2-sentence rationale for a service plan. "
        f"Providers selected: {provider_names}. "
        f"Needs covered: {', '.join(i.need_key for i in items)}. "
        f"Output JSON: {{\"rationale\": \"...\"}}."
    )
    result, used_fallback = complete_json(prompt, _RationaleResponse, _FALLBACK_RATIONALE)
    return result.rationale, used_fallback


def generate_plan(
    needs: list[str],
    negotiated_by_need: dict[str, list[NegotiatedOffer]],
    providers_by_id: dict[int, ProviderOut],
    budget_minor: int,
    currency: str,
) -> Optional[tuple[GeneratedPlan, bool]]:
    """
    Pick the best offer per need (highest score) that keeps total_minor <= budget_minor.
    Returns (GeneratedPlan, used_fallback) or None if nothing fits in budget.
    """
    # For each need, rank offers by score descending
    ranked: dict[str, list[NegotiatedOffer]] = {}
    for need in needs:
        offers = negotiated_by_need.get(need, [])
        ranked[need] = sorted(
            offers,
            key=lambda o: _score_item(o, providers_by_id[o.provider_id], budget_minor),
            reverse=True,
        )

    # Brute-force: try combinations (one per need) in score order
    # For small number of needs/providers this is fast enough
    need_lists = [ranked.get(n, []) for n in needs]
    if any(len(lst) == 0 for lst in need_lists):
        return None

    best_plan: Optional[GeneratedPlan] = None
    best_score = -1.0
    used_fallback = False

    for combo in itertools.product(*need_lists):
        total = sum(o.final_price_minor for o in combo)
        if total > budget_minor:
            continue

        score = sum(
            _score_item(o, providers_by_id[o.provider_id], budget_minor) for o in combo
        ) / len(combo)

        if score > best_score:
            best_score = score
            items = [
                PlanItem(
                    need_key=o.need_key,
                    provider_id=o.provider_id,
                    provider_name=providers_by_id[o.provider_id].name,
                    price_minor=o.final_price_minor,
                    scope=o.scope,
                    timeline_days=o.timeline_days,
                    offer_id=0,  # filled in by pipeline after DB insert
                )
                for o in combo
            ]
            rationale, used_fallback = _get_rationale(items)
            best_plan = GeneratedPlan(
                items=items,
                total_minor=total,
                currency=currency,
                rationale=rationale,
                score=best_score,
            )

    return (best_plan, used_fallback) if best_plan else None
