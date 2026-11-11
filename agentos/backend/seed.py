"""Database seed: the offline product catalog (app/search/catalog.py) and 1 demo user.

Idempotent upsert by listing_key and user email. Catalog prices are INR paise and are converted
to USD cents (the PayPal charge currency) by the same normalizer the live scraper uses.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import db as db_module
from app.models import User
from app.search.catalog import CATALOG
from app.search.normalize import to_provider_fields
from app.search.service import upsert_listing

DEMO_USER: dict[str, str] = {
    "name": "Aarav Sharma",
    "email": "demo@agentos.local",
}


def seed(db: Session) -> None:
    """Idempotently upsert the demo user and the catalog listings."""
    existing_user = db.execute(
        select(User).where(User.email == DEMO_USER["email"])
    ).scalar_one_or_none()
    if existing_user is None:
        db.add(User(name=DEMO_USER["name"], email=DEMO_USER["email"]))
    else:
        existing_user.name = DEMO_USER["name"]

    for listing_key, category, raw in CATALOG:
        upsert_listing(db, to_provider_fields(raw, category, listing_key=listing_key, source="catalog"))

    db.commit()


if __name__ == "__main__":
    db_module.init_engine()
    with db_module.SessionLocal() as session:
        seed(session)
