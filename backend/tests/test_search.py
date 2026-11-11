"""Product search: normalization, pure parsers, live fetch safety, and catalog fallback.

No real network: live fetches go through httpx.MockTransport.
"""

import json
from datetime import date

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Provider
from app.schemas import Need
from app.search import live, service
from app.search.normalize import RawListing, is_verified, pack_size_from_title, to_usd_minor
from app.search.parsers import (
    money_to_minor,
    parse_amazon_search,
    parse_delivery_days,
    parse_flipkart_search,
    parse_jsonld,
    parse_price_minor,
)

TODAY = date(2026, 11, 11)  # a Wednesday

# --------------------------------------------------------------------------- normalize


def test_to_usd_minor_uses_integer_ceil() -> None:
    assert to_usd_minor(25_000, "INR") == 298  # 297.6 -> 298
    assert to_usd_minor(4_000, "INR") == 48  # 47.6 -> 48
    assert to_usd_minor(8_400, "INR") == 100  # exact
    assert to_usd_minor(0, "INR") == 0
    assert to_usd_minor(1, "INR") == 1  # never rounds a charge down to zero
    assert to_usd_minor(1234, "USD") == 1234
    assert isinstance(to_usd_minor(19_900, "INR"), int)
    with pytest.raises(ValueError):
        to_usd_minor(100, "EUR")
    with pytest.raises(ValueError):
        to_usd_minor(-1, "INR")


@pytest.mark.parametrize(
    ("title", "size"),
    [
        ("Pack of 10 Metallic Party Hats", 10),
        ("Party Hats Combo, Set of 10", 10),
        ("Glitter Cone Hats (10 pcs)", 10),
        ("Latex Balloons 25 pcs", 25),
        ("Balloons 100 pieces", 100),
        ("Single Birthday Crown", 1),
    ],
)
def test_pack_size_from_title(title: str, size: int) -> None:
    assert pack_size_from_title(title) == size


def test_is_verified_requires_store_rating_and_reviews() -> None:
    assert is_verified("amazon", 4.4, 1_200) is True
    assert is_verified("Flipkart", 4.0, 50) is True
    assert is_verified("meesho", 4.9, 10_000) is False  # store not allowlisted
    assert is_verified("amazon", 3.9, 10_000) is False  # rating
    assert is_verified("amazon", 4.8, 49) is False  # review volume


# --------------------------------------------------------------------------- parsers


def test_money_parsing_is_exact_without_floats() -> None:
    assert money_to_minor("1,299.50") == 129_950
    assert money_to_minor("299") == 29_900
    assert money_to_minor("0.29") == 29
    assert money_to_minor("0") is None
    assert money_to_minor("abc") is None
    assert parse_price_minor("Now only ₹1,299 incl. taxes") == 129_900
    assert parse_price_minor("Rs. 250") == 25_000
    assert parse_price_minor("no price here") is None


def test_parse_delivery_days_with_fixed_today() -> None:
    assert parse_delivery_days("Get it Today", TODAY) == 0
    assert parse_delivery_days("FREE delivery Tomorrow", TODAY) == 1
    assert parse_delivery_days("Fri, 15 Nov", TODAY) == 4
    assert parse_delivery_days("Delivery by Nov 20", TODAY) == 9
    assert parse_delivery_days("by 2 Jan", TODAY) == 52  # rolls into next year
    assert parse_delivery_days("no date", TODAY) is None


AMAZON_HTML = """
<html><body>
<div data-component-type="s-search-result" data-asin="B0HATS">
  <h2><a href="/Metallic-Party-Hats/dp/B0HATS10?ref=sr_1"><span>Party Hats, Pack of 10</span></a></h2>
  <span class="a-icon-alt">4.4 out of 5 stars</span>
  <span aria-label="1,234 ratings"></span>
  <span class="a-price"><span class="a-price-whole">299</span><span class="a-price-fraction">50</span></span>
  <div>FREE delivery <b>Fri, 15 Nov</b></div>
</div>
<div data-component-type="s-search-result" data-asin="B0SPON">
  <span>Sponsored</span>
  <h2><span>Ad Hats</span></h2><a href="/ad/dp/B0SPON">x</a>
  <span class="a-price-whole">10</span>
</div>
<div data-component-type="s-search-result" data-asin="B0NOPRICE">
  <h2><a href="/x/dp/B0NOPRICE"><span>Unavailable hats</span></a></h2>
</div>
</body></html>
"""


def test_parse_amazon_search_block() -> None:
    out = parse_amazon_search(AMAZON_HTML, "https://www.amazon.in/s?k=party+hats", TODAY)
    assert len(out) == 1  # sponsored and price-less blocks skipped
    item = out[0]
    assert item.store == "amazon"
    assert item.title == "Party Hats, Pack of 10"
    assert item.url == "https://www.amazon.in/Metallic-Party-Hats/dp/B0HATS10"
    assert item.price_minor == 29_950
    assert item.shipping_minor == 0
    assert item.rating == 4.4
    assert item.review_count == 1_234
    assert item.delivery_days == 4


def test_parse_jsonld_product() -> None:
    ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Latex Balloons 25 pcs",
        "url": "/funfair-balloons/p/itm123",
        "aggregateRating": {"ratingValue": "4.3", "reviewCount": "870"},
        "offers": {"@type": "Offer", "price": "120.00", "priceCurrency": "INR", "seller": {"name": "FunFair"}},
    }
    page = f'<script type="application/ld+json">{json.dumps(ld)}</script><script type="application/ld+json">{{bad'
    out = parse_jsonld(page + "</script>", "flipkart", "https://www.flipkart.com/search?q=balloons")
    assert len(out) == 1
    item = out[0]
    assert item.price_minor == 12_000
    assert item.currency == "INR"
    assert item.rating == 4.3
    assert item.review_count == 870
    assert item.seller == "FunFair"
    assert item.url == "https://www.flipkart.com/funfair-balloons/p/itm123"


def test_parse_jsonld_numeric_price_and_unsupported_currency() -> None:
    good = {"@type": "Product", "name": "Hat", "offers": [{"price": 199.9, "priceCurrency": "INR"}]}
    eur = {"@type": "Product", "name": "Hat EU", "offers": {"price": "5", "priceCurrency": "EUR"}}
    page = "".join(
        f'<script type="application/ld+json">{json.dumps(x)}</script>' for x in ({"@graph": [good]}, eur)
    )
    out = parse_jsonld(page, "amazon", "https://www.amazon.in/")
    assert [(o.title, o.price_minor) for o in out] == [("Hat", 19_990)]


FLIPKART_HTML = """
<div class="row">
  <a class="x1" href="/partyzone-metallic-party-hats/p/itm0001?pid=ABC" title="Pack of 10 Metallic Party Hats">
    <img src="i.jpg"/></a>
  <div><span>4.2</span><span>3,100 Ratings</span></div>
  <div>&#8377;250</div><div>Delivery by 15 Nov</div>
</div>
<div class="row">
  <a href="/partyzone-metallic-party-hats/p/itm0001?pid=DUP" title="Duplicate link">dup</a>
</div>
"""


def test_parse_flipkart_anchor_and_price() -> None:
    out = parse_flipkart_search(FLIPKART_HTML, "https://www.flipkart.com/search?q=party+hats", TODAY)
    assert len(out) == 1  # duplicate product path deduped
    item = out[0]
    assert item.store == "flipkart"
    assert item.title == "Pack of 10 Metallic Party Hats"
    assert item.url == "https://www.flipkart.com/partyzone-metallic-party-hats/p/itm0001"
    assert item.price_minor == 25_000
    assert item.rating == 4.2
    assert item.review_count == 3_100
    assert item.delivery_days == 4


def test_parsers_return_empty_on_unreadable_markup() -> None:
    junk = "<html><body><div id='captcha'>Robot check</div></body></html>"
    assert parse_amazon_search(junk, "https://www.amazon.in/") == []
    assert parse_flipkart_search(junk, "https://www.flipkart.com/") == []
    assert parse_jsonld(junk, "amazon", "https://www.amazon.in/") == []


# --------------------------------------------------------------------------- live fetch safety


@pytest.fixture()
def mock_http(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    """Route live.fetch through an httpx.MockTransport; returns the list of requested URLs."""
    real_client = httpx.Client
    requested: list[str] = []
    routes: dict[str, httpx.Response] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return routes.get(str(request.url), httpx.Response(404))

    def factory(**kwargs):  # type: ignore[no-untyped-def]
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(live.httpx, "Client", factory)
    return routes, requested


def test_fetch_rejects_non_allowlisted_host_and_non_https(mock_http) -> None:  # type: ignore[no-untyped-def]
    _, requested = mock_http
    with pytest.raises(live.SearchError, match="not allowlisted"):
        live.fetch("https://evil.example.com/s?k=hats")
    with pytest.raises(live.SearchError, match="non-HTTPS"):
        live.fetch("http://www.amazon.in/s?k=hats")
    assert requested == []  # rejected before any request


def test_fetch_follows_allowlisted_redirect_only(mock_http) -> None:  # type: ignore[no-untyped-def]
    routes, requested = mock_http
    routes["https://amazon.in/s?k=a"] = httpx.Response(301, headers={"location": "https://www.amazon.in/s?k=a"})
    routes["https://www.amazon.in/s?k=a"] = httpx.Response(200, text="<html>ok</html>")
    assert live.fetch("https://amazon.in/s?k=a") == "<html>ok</html>"

    routes["https://www.amazon.in/s?k=b"] = httpx.Response(302, headers={"location": "https://evil.example.com/x"})
    with pytest.raises(live.SearchError, match="not allowlisted"):
        live.fetch("https://www.amazon.in/s?k=b")
    assert "https://evil.example.com/x" not in requested


def test_fetch_rejects_redirect_loops_and_errors(mock_http) -> None:  # type: ignore[no-untyped-def]
    routes, _ = mock_http
    routes["https://www.amazon.in/loop"] = httpx.Response(302, headers={"location": "/loop"})
    with pytest.raises(live.SearchError, match="Too many redirects"):
        live.fetch("https://www.amazon.in/loop")
    routes["https://www.amazon.in/blocked"] = httpx.Response(503)
    with pytest.raises(live.SearchError, match="HTTP 503"):
        live.fetch("https://www.amazon.in/blocked")


def test_fetch_rejects_oversize_body(mock_http, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    routes, _ = mock_http
    monkeypatch.setattr(settings, "SEARCH_MAX_BYTES", 100)
    routes["https://www.flipkart.com/big"] = httpx.Response(200, content=b"x" * 101)
    with pytest.raises(live.SearchError, match="exceeds"):
        live.fetch("https://www.flipkart.com/big")


def test_search_store_parses_and_caps_listings(mock_http, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    routes, _ = mock_http
    monkeypatch.setattr(settings, "MAX_LISTINGS_PER_STORE", 1)
    routes["https://www.amazon.in/s?k=party+hats"] = httpx.Response(200, text=AMAZON_HTML * 3)
    out = live.search_store("amazon", "party hats")
    assert len(out) == 1
    routes["https://www.flipkart.com/search?q=hats"] = httpx.Response(200, text="<html>captcha</html>")
    with pytest.raises(live.SearchError, match="No parseable listings"):
        live.search_store("flipkart", "hats")
    with pytest.raises(live.SearchError):
        live.search_store("meesho", "hats")


# --------------------------------------------------------------------------- service


NEEDS = [
    Need(key="party_hats", category="party_hats", quantity=10),
    Need(key="balloons", category="balloons", quantity=50),
]


def test_find_listings_mock_mode_returns_catalog(db: Session) -> None:
    assert settings.SEARCH_MODE == "mock"
    out = service.find_listings(db, NEEDS)
    assert out.mode == "mock"
    assert out.fallbacks == []
    assert len(out.listings) == 6
    assert all(p.source == "catalog" for p in out.listings)


def test_find_listings_live_failure_falls_back_to_catalog(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SEARCH_MODE", "live")

    def boom(store: str, query: str) -> list[RawListing]:
        raise live.SearchError(f"HTTP 503 from {store}")

    monkeypatch.setattr(live, "search_store", boom)
    out = service.find_listings(db, NEEDS[:1])
    assert out.mode == "live"
    assert {p.category for p in out.listings} == {"party_hats"}
    assert all(p.source == "catalog" for p in out.listings)
    assert out.live_counts == {"party_hats:amazon": 0, "party_hats:flipkart": 0}
    assert any("HTTP 503" in f for f in out.fallbacks)
    assert any("offline catalog" in f for f in out.fallbacks)


def test_find_listings_live_success_upserts_rows(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "SEARCH_MODE", "live")
    monkeypatch.setattr(settings, "SEARCH_STORES", ["amazon"])
    raw = RawListing(
        store="amazon",
        title="Party Hats, Pack of 10",
        url="https://www.amazon.in/dp/LIVEHATS",
        price_minor=29_950,
        rating=4.4,
        review_count=1_234,
        delivery_days=2,
    )
    monkeypatch.setattr(live, "search_store", lambda store, query: [raw])

    out = service.find_listings(db, NEEDS[:1])
    assert out.fallbacks == []
    assert out.live_counts == {"party_hats:amazon": 1}
    assert len(out.listings) == 1
    listing = out.listings[0]
    assert listing.source == "live"
    assert listing.listing_key == raw.url
    assert listing.base_price_minor == listing.min_price_minor == to_usd_minor(29_950, "INR") == 357
    assert listing.original_price_minor == 29_950
    assert listing.pack_size == 10
    assert listing.verified is True
    assert listing.name.startswith("Amazon")

    # Second search upserts the same URL instead of duplicating it
    service.find_listings(db, NEEDS[:1])
    rows = db.scalars(select(Provider).where(Provider.source == "live")).all()
    assert len(rows) == 1
    assert rows[0].listing_key == raw.url
