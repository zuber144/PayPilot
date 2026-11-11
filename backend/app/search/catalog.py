"""Offline demo catalog (SEARCH_MODE=mock and live-mode fallback).

Prices are INR paise as a store would show them; conversion to USD cents happens in
`normalize.to_provider_fields`. Verification is derived (store allowlist + rating + reviews),
not hard-coded. Tuned for the four demo scenarios (DECISIONS.md #18):

clean   10 hats + 50 balloons -> PartyZone (Flipkart) 346 + Balloon Bazaar (Amazon) 237 = 583 cents
retry   strict min_rating 4.5 leaves 0 verified hats -> retry relaxes rating
blocked unverified Meesho sellers are cheapest when include_unverified is set
review  20 hats only -> one seller holds 100% -> SINGLE_VENDOR_SHARE REVIEW
"""

from __future__ import annotations

from app.search.normalize import RawListing

# (listing_key, category, listing)
CATALOG: list[tuple[str, str, RawListing]] = [
    (
        "catalog:flipkart:partyzone-hats-10",
        "party_hats",
        RawListing(
            store="flipkart",
            title="Pack of 10 Metallic Party Hats",
            url="https://www.flipkart.com/partyzone-metallic-party-hats/p/itm-demo-hats10",
            price_minor=25_000,  # INR 250
            shipping_minor=4_000,  # INR 40 delivery fee
            rating=4.2,
            review_count=3_100,
            delivery_days=4,
            seller="PartyZone Official",
        ),
    ),
    (
        "catalog:amazon:celebrations-hats-10",
        "party_hats",
        RawListing(
            store="amazon",
            title="Party Hats Combo, Set of 10",
            url="https://www.amazon.in/dp/DEMOHATS10",
            price_minor=30_000,  # INR 300, free delivery
            rating=4.4,
            review_count=1_200,
            delivery_days=2,
            seller="Celebrations Hub",
        ),
    ),
    (
        "catalog:meesho:partyking-hats-10",
        "party_hats",
        RawListing(
            store="meesho",
            title="Glitter Cone Hats (10 pcs)",
            url="https://www.meesho.com/demo-glitter-cone-hats/p/demo1",
            price_minor=15_000,  # INR 150
            rating=3.6,
            review_count=14,
            delivery_days=7,
            seller="PartyKing Store",
        ),
    ),
    (
        "catalog:amazon:balloonbazaar-50",
        "balloons",
        RawListing(
            store="amazon",
            title="Metallic Balloons, Pack of 50",
            url="https://www.amazon.in/dp/DEMOBALL50",
            price_minor=19_900,  # INR 199, free delivery
            rating=4.5,
            review_count=5_400,
            delivery_days=1,
            seller="Balloon Bazaar",
        ),
    ),
    (
        "catalog:flipkart:funfair-balloons-25",
        "balloons",
        RawListing(
            store="flipkart",
            title="Latex Balloons 25 pcs",
            url="https://www.flipkart.com/funfair-latex-balloons/p/itm-demo-ball25",
            price_minor=12_000,  # INR 120
            rating=4.3,
            review_count=870,
            delivery_days=3,
            seller="FunFair Supplies",
        ),
    ),
    (
        "catalog:meesho:cheapdeals-balloons-100",
        "balloons",
        RawListing(
            store="meesho",
            title="Balloons 100 pcs",
            url="https://www.meesho.com/demo-balloons-100/p/demo2",
            price_minor=9_900,  # INR 99
            rating=3.2,
            review_count=8,
            delivery_days=8,
            seller="Cheap Deals 4U",
        ),
    ),
]
