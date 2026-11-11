"""Deterministic listing normalization: integer FX, pack size, seller verification.

Every number here is computed in code. The LLM never sees or sets a price.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

from app.config import settings


class RawListing(BaseModel):
    """A listing as extracted from a store page or the offline catalog (native currency)."""

    store: str  # lower-case store id, e.g. "amazon"
    title: str
    url: str
    price_minor: int  # one pack, native minor units (paise)
    shipping_minor: int = 0  # native minor units
    currency: str = "INR"
    rating: float = 0.0
    review_count: int = 0
    delivery_days: int | None = None
    seller: str = ""


def to_usd_minor(amount_minor: int, currency: str) -> int:
    """Convert native minor units to USD cents with integer ceil division (never undercharge)."""
    if amount_minor < 0:
        raise ValueError("amount_minor must be non-negative")
    code = currency.upper()
    if code == "USD":
        return amount_minor
    if code == "INR":
        return -(-amount_minor * 100 // settings.INR_PAISE_PER_USD)
    raise ValueError(f"Unsupported listing currency: {currency}")


_PACK_PATTERNS = [
    re.compile(r"(?:pack|set|box|bundle|combo)\s+of\s+(\d{1,4})", re.IGNORECASE),
    re.compile(r"(\d{1,4})\s*(?:pcs|pc|pieces|piece|pack|count|ct|nos|units)\b", re.IGNORECASE),
    re.compile(r"\((\d{1,4})\s*(?:pcs|pieces)?\)", re.IGNORECASE),
]


def pack_size_from_title(title: str) -> int:
    """Units per pack parsed from the title ("Pack of 10", "50 pcs"); defaults to 1."""
    for pattern in _PACK_PATTERNS:
        match = pattern.search(title)
        if match:
            n = int(match.group(1))
            if n >= 1:
                return n
    return 1


def is_verified(store: str, rating: float, review_count: int) -> bool:
    """Verified seller = allowlisted store AND rating AND review volume thresholds."""
    return (
        store.lower() in {s.lower() for s in settings.VERIFIED_STORES}
        and rating >= settings.VERIFIED_MIN_RATING
        and review_count >= settings.VERIFIED_MIN_REVIEWS
    )


def store_label(store: str) -> str:
    return store[:1].upper() + store[1:] if store else ""


def to_provider_fields(
    raw: RawListing, category: str, *, listing_key: str, source: str
) -> dict[str, Any]:
    """Map a RawListing to `models.Provider` column values (USD cents + native display values)."""
    pack_usd = to_usd_minor(raw.price_minor, raw.currency)
    ship_usd = to_usd_minor(raw.shipping_minor, raw.currency)
    label = store_label(raw.store)
    seller = raw.seller.strip()
    display = f"{seller} ({label})" if seller else f"{label}: {raw.title[:60]}"
    delivery = raw.delivery_days if raw.delivery_days is not None else settings.SEARCH_DEFAULT_DELIVERY_DAYS
    return {
        "listing_key": listing_key[:300],
        "name": display[:200],
        "category": category[:50],
        "base_price_minor": pack_usd,
        "min_price_minor": pack_usd,
        "concession_rate": 0.0,
        "rating": float(raw.rating),
        "turnaround_days": max(0, int(delivery)),
        "verified": is_verified(raw.store, raw.rating, raw.review_count),
        "currency": "USD",
        "persona": raw.title[:500],
        "store": raw.store.lower()[:50],
        "product_title": raw.title[:500],
        "url": raw.url,
        "pack_size": pack_size_from_title(raw.title),
        "shipping_minor": ship_usd,
        "review_count": int(raw.review_count),
        "original_currency": raw.currency.upper(),
        "original_price_minor": raw.price_minor,
        "original_shipping_minor": raw.shipping_minor,
        "source": source,
    }
