"""Listing lookup used by the discovery node.

mock: the seeded offline catalog (`providers.source == "catalog"`), no network.
live: scrape each allowlisted store per need and upsert listings (keyed by URL); any store or
need that fails falls back to the catalog and is reported so the graph writes a FALLBACK event.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Provider
from app.schemas import Need, ProviderOut
from app.search import live
from app.search.normalize import RawListing, to_provider_fields


@dataclass
class SearchOutcome:
    listings: list[ProviderOut]
    mode: str
    fallbacks: list[str] = field(default_factory=list)  # human-readable fallback reasons
    live_counts: dict[str, int] = field(default_factory=dict)  # "<need>:<store>" -> listings


def _catalog(db: Session) -> list[ProviderOut]:
    rows = db.scalars(select(Provider).where(Provider.source == "catalog").order_by(Provider.id)).all()
    return [ProviderOut.model_validate(r) for r in rows]


def upsert_listing(db: Session, fields: dict[str, Any]) -> Provider:
    row = db.scalars(select(Provider).where(Provider.listing_key == fields["listing_key"])).first()
    if row is None:
        row = Provider(**fields)
        db.add(row)
    else:
        for key, value in fields.items():
            setattr(row, key, value)
    db.flush()
    return row


def _query_for(need: Need) -> str:
    words = need.category.replace("_", " ")
    if need.must_haves:
        words = f"{words} {' '.join(need.must_haves[:3])}"
    return words[:120]


def find_listings(db: Session, needs: list[Need]) -> SearchOutcome:
    """Return candidate listings for `needs` (does not commit; the graph commits per node)."""
    catalog = _catalog(db)
    if settings.SEARCH_MODE != "live":
        return SearchOutcome(listings=catalog, mode="mock")

    outcome = SearchOutcome(listings=[], mode="live")
    fallback_categories: set[str] = set()
    for need in needs:
        found = 0
        for store in settings.SEARCH_STORES:
            key = f"{need.key}:{store}"
            try:
                raws: list[RawListing] = live.search_store(store, _query_for(need))
            except live.SearchError as exc:
                outcome.fallbacks.append(f"{key}: {exc}")
                outcome.live_counts[key] = 0
                continue
            for raw in raws:
                row = upsert_listing(
                    db, to_provider_fields(raw, need.category, listing_key=raw.url, source="live")
                )
                outcome.listings.append(ProviderOut.model_validate(row))
            outcome.live_counts[key] = len(raws)
            found += len(raws)
        if found == 0:
            fallback_categories.add(need.category.lower())
    if fallback_categories:
        outcome.listings.extend(p for p in catalog if p.category.lower() in fallback_categories)
        outcome.fallbacks.append(
            f"Used offline catalog for: {', '.join(sorted(fallback_categories))}"
        )
    return outcome
