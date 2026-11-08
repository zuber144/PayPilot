"""
app/agents/discovery.py — Step 2: SQL-based service discovery.

Finds and ranks providers from the DB for each need in the parsed goal.
No LLM used here — pure SQL + Python ranking.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Provider
from app.schemas import DiscoveryResult, ProviderOut


def discover_providers(
    db: Session,
    needs: list[str],
    budget_minor: int,
    currency: str,
    max_per_need: int = 3,
) -> list[DiscoveryResult]:
    """
    For each need key, find up to `max_per_need` providers from the DB.

    Ranking: verified first, then by rating desc, then by base_price_minor asc.
    Filters: base_price_minor <= budget_minor (don't surface obviously unaffordable providers).
    """
    results: list[DiscoveryResult] = []

    for need_key in needs:
        # Category matches the need_key OR the category name contains the need keyword
        need_parts = need_key.split("_")  # e.g. "web_design" -> ["web", "design"]

        stmt = (
            select(Provider)
            .where(Provider.base_price_minor <= budget_minor)
            .order_by(
                Provider.verified.desc(),
                Provider.rating.desc(),
                Provider.base_price_minor.asc(),
            )
        )
        all_providers: list[Provider] = list(db.execute(stmt).scalars().all())

        # Filter by category relevance: exact match first, then keyword match
        exact = [p for p in all_providers if p.category.lower() == need_key.lower()]
        if exact:
            matched = exact
        else:
            matched = [
                p for p in all_providers
                if any(part in p.category.lower() for part in need_parts)
            ]

        # Fallback: if no category match, return top-rated providers anyway
        if not matched:
            matched = all_providers

        top = matched[:max_per_need]

        results.append(
            DiscoveryResult(
                need_key=need_key,
                providers=[ProviderOut.model_validate(p) for p in top],
            )
        )

    return results
