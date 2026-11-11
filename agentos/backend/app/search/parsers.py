"""Pure HTML parsers for store search/product pages. No network, no LLM.

Prices are parsed with integer/Decimal arithmetic from visible text or JSON-LD, never floats.
Store markup changes often; every parser returns [] (never raises) on markup it cannot read, and
the search service then falls back to the offline catalog with a FALLBACK trace event.
"""

from __future__ import annotations

import html as html_lib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urljoin

from app.search.normalize import RawListing

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_PRICE_RE = re.compile(r"(?:₹|&#8377;|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE)
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1
)}


def strip_tags(fragment: str) -> str:
    return _WS_RE.sub(" ", html_lib.unescape(_TAG_RE.sub(" ", fragment))).strip()


def money_to_minor(text: str) -> int | None:
    """'1,299.50' -> 129950; '299' -> 29900. Decimal, never float."""
    cleaned = text.replace(",", "").strip()
    if not cleaned:
        return None
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    if value <= 0:
        return None
    return int((value * 100).to_integral_value())


def parse_price_minor(text: str) -> int | None:
    """First rupee amount in `text` ("₹1,299", "Rs. 250") as paise."""
    match = _PRICE_RE.search(text)
    return money_to_minor(match.group(1)) if match else None


def parse_delivery_days(text: str, today: date | None = None) -> int | None:
    """'Tomorrow' -> 1, 'Today' -> 0, 'Fri, 15 Nov' / 'by 15 Nov' -> days from today."""
    today = today or date.today()
    lowered = text.lower()
    if "today" in lowered:
        return 0
    if "tomorrow" in lowered:
        return 1
    match = re.search(r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*", lowered)
    if not match:
        match_rev = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})\b", lowered)
        if not match_rev:
            return None
        day, month = int(match_rev.group(2)), _MONTHS[match_rev.group(1)]
    else:
        day, month = int(match.group(1)), _MONTHS[match.group(2)]
    try:
        target = date(today.year, month, day)
    except ValueError:
        return None
    if target < today:
        try:
            target = date(today.year + 1, month, day)
        except ValueError:
            return None
    delta = (target - today).days
    return delta if delta <= 60 else None


def _int_from(text: str) -> int:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


# --------------------------------------------------------------------------- JSON-LD


def _iter_ld_nodes(obj: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    stack = [obj]
    while stack and len(out) < 500:
        cur = stack.pop()
        if isinstance(cur, list):
            stack.extend(cur)
        elif isinstance(cur, dict):
            out.append(cur)
            for key in ("@graph", "itemListElement", "item", "mainEntity"):
                if key in cur:
                    stack.append(cur[key])
    return out


def _is_type(node: dict[str, Any], name: str) -> bool:
    t = node.get("@type")
    return t == name or (isinstance(t, list) and name in t)


def parse_jsonld(page: str, store: str, base_url: str) -> list[RawListing]:
    """Extract schema.org Product nodes (name, offers.price, aggregateRating) from JSON-LD."""
    results: list[RawListing] = []
    for block in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', page, re.DOTALL | re.IGNORECASE
    ):
        try:
            data = json.loads(block.strip())
        except (json.JSONDecodeError, ValueError):
            continue
        for node in _iter_ld_nodes(data):
            if not _is_type(node, "Product"):
                continue
            offers = node.get("offers")
            if isinstance(offers, list):
                offers = offers[0] if offers else None
            if not isinstance(offers, dict):
                continue
            currency = str(offers.get("priceCurrency") or "INR").upper()
            raw_price = offers.get("price", offers.get("lowPrice"))
            if raw_price is None or currency not in ("INR", "USD"):
                continue
            price = money_to_minor(str(raw_price))
            title = strip_tags(str(node.get("name") or ""))
            if price is None or not title:
                continue
            agg = node.get("aggregateRating")
            rating_node: dict[str, Any] = agg if isinstance(agg, dict) else {}
            try:
                rating = float(str(rating_node.get("ratingValue", 0)))
            except ValueError:
                rating = 0.0
            reviews = _int_from(str(rating_node.get("reviewCount") or rating_node.get("ratingCount") or 0))
            seller = offers.get("seller")
            seller_name = str(seller.get("name") or "") if isinstance(seller, dict) else ""
            url = urljoin(base_url, str(node.get("url") or offers.get("url") or base_url))
            results.append(
                RawListing(
                    store=store,
                    title=title,
                    url=url,
                    price_minor=price,
                    currency=currency,
                    rating=rating,
                    review_count=reviews,
                    seller=seller_name,
                )
            )
    return results


# --------------------------------------------------------------------------- Amazon search page


def parse_amazon_search(page: str, base_url: str, today: date | None = None) -> list[RawListing]:
    """Parse `div[data-component-type="s-search-result"]` blocks on an Amazon search page."""
    results: list[RawListing] = []
    chunks = re.split(r'data-component-type=["\']s-search-result["\']', page)[1:]
    for chunk in chunks:
        block = chunk[:20_000]
        title_match = re.search(r"<h2[^>]*>(.*?)</h2>", block, re.DOTALL)
        head = block[: title_match.start()] if title_match else block[:600]
        if "AdHolder" in head or "Sponsored" in head:  # ad label sits above this result's title
            continue
        href_match = re.search(r'href=["\']([^"\']*/dp/[^"\']+)["\']', block)
        whole = re.search(r'class=["\']a-price-whole["\'][^>]*>([\d,]+)', block)
        if not (title_match and href_match and whole):
            continue
        frac = re.search(r'class=["\']a-price-fraction["\'][^>]*>(\d{1,2})', block)
        price = money_to_minor(whole.group(1) + ("." + frac.group(1) if frac else ""))
        title = strip_tags(title_match.group(1))
        if price is None or not title:
            continue
        rating_match = re.search(r"([0-5](?:\.\d)?) out of 5 stars", block)
        reviews_match = re.search(r'aria-label=["\']([\d,]+) (?:ratings?|reviews?)["\']', block) or re.search(
            r's-underline-text["\'][^>]*>\(?([\d,.]+K?)\)?<', block
        )
        reviews = 0
        if reviews_match:
            raw_rev = reviews_match.group(1)
            reviews = _int_from(raw_rev) * (1000 if raw_rev.upper().endswith("K") else 1)
            if raw_rev.upper().endswith("K") and "." in raw_rev:
                reviews = int(Decimal(raw_rev[:-1]) * 1000)
        text = strip_tags(block)
        free = "free delivery" in text.lower()
        ship_match = re.search(r"(?:₹|Rs\.?)\s*([\d,]+)\s*delivery", text, re.IGNORECASE)
        shipping = 0 if free or not ship_match else (money_to_minor(ship_match.group(1)) or 0)
        delivery_match = re.search(r"delivery\s+(?:by\s+)?((?:today|tomorrow|[A-Za-z]{3},?\s+\d{1,2}\s+[A-Za-z]{3}))",
                                   text, re.IGNORECASE)
        results.append(
            RawListing(
                store="amazon",
                title=title,
                url=urljoin(base_url, html_lib.unescape(href_match.group(1)).split("?")[0]),
                price_minor=price,
                shipping_minor=shipping,
                rating=float(rating_match.group(1)) if rating_match else 0.0,
                review_count=reviews,
                delivery_days=parse_delivery_days(delivery_match.group(1), today) if delivery_match else None,
                seller="",
            )
        )
    return results


# --------------------------------------------------------------------------- Flipkart search page


def parse_flipkart_search(page: str, base_url: str, today: date | None = None) -> list[RawListing]:
    """JSON-LD first; otherwise pair each product link (`/p/itm...`) with the next rupee price."""
    ld = parse_jsonld(page, "flipkart", base_url)
    if ld:
        return ld
    results: list[RawListing] = []
    seen: set[str] = set()
    for match in re.finditer(r'<a[^>]+href=["\'](/[^"\']*/p/itm[^"\']*)["\'][^>]*>(.*?)</a>', page, re.DOTALL):
        path = html_lib.unescape(match.group(1)).split("?")[0]
        if path in seen:
            continue
        anchor_tag = match.group(0)[: match.group(0).find(">") + 1]
        title_attr = re.search(r'title=["\']([^"\']+)["\']', anchor_tag)
        title = html_lib.unescape(title_attr.group(1)) if title_attr else strip_tags(match.group(2))
        window = page[match.end(): match.end() + 2_500]
        price = parse_price_minor(strip_tags(window))
        if not title or price is None or len(title) < 4:
            continue
        seen.add(path)
        win_text = strip_tags(window)
        rating_match = re.search(r"\b([1-5]\.\d)\b", win_text)
        reviews_match = re.search(r"([\d,]+)\s+Ratings", win_text, re.IGNORECASE)
        delivery_match = _FK_DELIVERY_RE.search(win_text)
        results.append(
            RawListing(
                store="flipkart",
                title=title,
                url=urljoin(base_url, path),
                price_minor=price,
                rating=float(rating_match.group(1)) if rating_match else 0.0,
                review_count=_int_from(reviews_match.group(1)) if reviews_match else 0,
                delivery_days=parse_delivery_days(delivery_match.group(1), today) if delivery_match else None,
                seller="",
            )
        )
    return results


_FK_DELIVERY_RE = re.compile(
    r"(?:delivery|by)\s+((?:today|tomorrow|[A-Za-z]{3},?\s+[A-Za-z]{3}\s+\d{1,2}|\d{1,2}\s+[A-Za-z]{3}))",
    re.IGNORECASE,
)

PARSERS = {
    "amazon": parse_amazon_search,
    "flipkart": parse_flipkart_search,
}
