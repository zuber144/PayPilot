"""Database seed: 6 demo providers (work-division doc 3.7) and 1 demo user.

Idempotent upsert by provider name and user email. All prices are in paise (INR * 100).
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import db as db_module
from app.models import Provider, User

DEMO_USER: dict[str, str] = {
    "name": "Aarav Sharma",
    "email": "demo@agentos.local",
}

SEED_PROVIDERS: list[dict[str, Any]] = [
    {
        "name": "ABC Catering",
        "category": "catering",
        "base_price_minor": 2_800_000,  # INR 28,000
        "min_price_minor": 2_400_000,  # INR 24,000
        "concession_rate": 0.0375,
        "rating": 4.6,
        "turnaround_days": 7,
        "verified": True,
        "currency": "INR",
        "persona": "Trusted corporate and event caterer with full-service buffet setups.",
    },
    {
        "name": "Spice Route Caterers",
        "category": "catering",
        "base_price_minor": 3_200_000,  # INR 32,000
        "min_price_minor": 2_700_000,  # INR 27,000
        "concession_rate": 0.04,
        "rating": 4.4,
        "turnaround_days": 6,
        "verified": True,
        "currency": "INR",
        "persona": "Premium regional Indian cuisine specialist with live stations.",
    },
    {
        "name": "QuickBites Co",
        "category": "catering",
        "base_price_minor": 2_200_000,  # INR 22,000
        "min_price_minor": 2_000_000,  # INR 20,000
        "concession_rate": 0.04,
        "rating": 4.1,
        "turnaround_days": 5,
        "verified": False,
        "currency": "INR",
        "persona": "Low-cost express event caterer for casual parties.",
    },
    {
        "name": "Studio X",
        "category": "photography",
        "base_price_minor": 1_800_000,  # INR 18,000
        "min_price_minor": 1_500_000,  # INR 15,000
        "concession_rate": 0.0385,
        "rating": 4.7,
        "turnaround_days": 4,
        "verified": True,
        "currency": "INR",
        "persona": "Award-winning event photography studio with rapid 4-day delivery.",
    },
    {
        "name": "LensCraft",
        "category": "photography",
        "base_price_minor": 2_100_000,  # INR 21,000
        "min_price_minor": 1_750_000,  # INR 17,500
        "concession_rate": 0.04,
        "rating": 4.2,
        "turnaround_days": 9,
        "verified": True,
        "currency": "INR",
        "persona": "Candid and documentary event photographers with full gallery delivery.",
    },
    {
        "name": "PixelNest",
        "category": "photography",
        "base_price_minor": 1_400_000,  # INR 14,000
        "min_price_minor": 1_200_000,  # INR 12,000
        "concession_rate": 0.05,
        "rating": 4.5,
        "turnaround_days": 3,
        "verified": False,
        "currency": "INR",
        "persona": "Freelance rapid-turnaround photo crew for compact events.",
    },
]


def seed(db: Session) -> None:
    """Idempotently upsert the demo user and the six demo providers."""
    existing_user = db.execute(
        select(User).where(User.email == DEMO_USER["email"])
    ).scalar_one_or_none()
    if existing_user is None:
        db.add(User(name=DEMO_USER["name"], email=DEMO_USER["email"]))
    else:
        existing_user.name = DEMO_USER["name"]

    for pdata in SEED_PROVIDERS:
        existing_provider = db.execute(
            select(Provider).where(Provider.name == pdata["name"])
        ).scalar_one_or_none()
        if existing_provider is None:
            db.add(Provider(**pdata))
        else:
            for field, value in pdata.items():
                setattr(existing_provider, field, value)

    db.commit()


if __name__ == "__main__":
    db_module.init_engine()
    with db_module.SessionLocal() as session:
        seed(session)
