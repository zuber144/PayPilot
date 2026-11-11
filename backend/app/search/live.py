"""Live store search (SEARCH_MODE=live): fetch allowlisted search pages and parse them.

Safety: only hosts in SEARCH_ALLOWED_HOSTS (every redirect hop re-checked, at most
SEARCH_MAX_REDIRECTS), HTTPS only, response size capped at SEARCH_MAX_BYTES, timeout
SEARCH_TIMEOUT_SECONDS, generic User-Agent with no user details. Store pages are often
JS-rendered or bot-walled; any failure raises SearchError and the caller falls back to the
offline catalog.
"""

from __future__ import annotations

from urllib.parse import quote_plus, urljoin, urlparse

import httpx

from app.config import settings
from app.search.normalize import RawListing
from app.search.parsers import PARSERS

STORE_SEARCH_URLS: dict[str, str] = {
    "amazon": "https://www.amazon.in/s?k={q}",
    "flipkart": "https://www.flipkart.com/search?q={q}",
}


class SearchError(Exception):
    pass


def _check_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise SearchError(f"Refusing non-HTTPS URL: {parsed.scheme}://{parsed.hostname}")
    host = (parsed.hostname or "").lower()
    if host not in {h.lower() for h in settings.SEARCH_ALLOWED_HOSTS}:
        raise SearchError(f"Host not allowlisted: {host}")


def fetch(url: str) -> str:
    """GET `url` with allowlist, redirect, size and timeout limits. Returns decoded HTML."""
    headers = {"User-Agent": settings.SEARCH_USER_AGENT, "Accept": "text/html", "Accept-Language": "en-IN,en"}
    current = url
    try:
        with httpx.Client(timeout=settings.SEARCH_TIMEOUT_SECONDS, follow_redirects=False, headers=headers) as client:
            for _ in range(settings.SEARCH_MAX_REDIRECTS + 1):
                _check_url(current)
                with client.stream("GET", current) as resp:
                    if resp.is_redirect:
                        location = resp.headers.get("location", "")
                        if not location:
                            raise SearchError("Redirect without Location header")
                        current = urljoin(current, location)
                        continue
                    if resp.status_code != 200:
                        raise SearchError(f"HTTP {resp.status_code} from {urlparse(current).hostname}")
                    body = bytearray()
                    for chunk in resp.iter_bytes():
                        body.extend(chunk)
                        if len(body) > settings.SEARCH_MAX_BYTES:
                            raise SearchError(f"Response exceeds {settings.SEARCH_MAX_BYTES} bytes")
                    return body.decode(resp.encoding or "utf-8", errors="replace")
    except httpx.HTTPError as exc:
        raise SearchError(f"{type(exc).__name__} fetching {urlparse(current).hostname}") from exc
    raise SearchError(f"Too many redirects (>{settings.SEARCH_MAX_REDIRECTS})")


def search_store(store: str, query: str) -> list[RawListing]:
    """Search one store for `query`; returns at most MAX_LISTINGS_PER_STORE parsed listings."""
    template = STORE_SEARCH_URLS.get(store)
    parser = PARSERS.get(store)
    if template is None or parser is None:
        raise SearchError(f"No live search support for store '{store}'")
    url = template.format(q=quote_plus(query))
    page = fetch(url)
    listings = parser(page, url)
    if not listings:
        raise SearchError(f"No parseable listings on {store} (page may be JS-rendered or blocked)")
    return listings[: settings.MAX_LISTINGS_PER_STORE]
