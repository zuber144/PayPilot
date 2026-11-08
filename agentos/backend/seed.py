"""
seed.py — populate the DB with demo data.

Run from the backend/ directory:
  python seed.py

Creates:
  - 1 demo user
  - 8 providers across 4 categories
  - 3 demo goals (designed to produce APPROVED / REVIEW / BLOCKED outcomes)
"""
from __future__ import annotations

import sys
import os

# Allow running from backend/ directory
sys.path.insert(0, os.path.dirname(__file__))

from app.db import Base, SessionLocal, engine
from app.models import Goal, Offer, Plan, Provider, Transaction, User

# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # ── Clear existing seed data ─────────────────────────────────────────────
    db.query(Transaction).delete()
    db.query(Plan).delete()
    db.query(Offer).delete()
    db.query(Goal).delete()
    db.query(Provider).delete()
    db.query(User).delete()
    db.commit()

    # ── Demo user ────────────────────────────────────────────────────────────
    user = User(id=1, name="Alex Demo", email="alex@demo.paypilot.dev")
    db.add(user)
    db.commit()

    # ── Providers (8, across 4 categories) ──────────────────────────────────
    #
    # Categories: web_design, copywriting, logo_design, marketing
    #
    # Money in minor units (USD cents). E.g. 50000 = $500.00
    #
    providers = [
        # --- web_design ---
        Provider(
            id=1,
            name="PixelCraft Studio",
            category="web_design",
            base_price_minor=80000,   # $800
            min_price_minor=55000,    # $550
            concession_rate=0.15,
            rating=4.8,
            turnaround_days=10,
            verified=True,
            persona="Professional web design agency specialising in e-commerce and SaaS brands.",
        ),
        Provider(
            id=2,
            name="QuickSite Co",
            category="web_design",
            base_price_minor=45000,   # $450
            min_price_minor=30000,    # $300
            concession_rate=0.20,
            rating=4.1,
            turnaround_days=7,
            verified=True,
            persona="Fast-turnaround web design for startups on a budget.",
        ),
        # --- copywriting ---
        Provider(
            id=3,
            name="WordSmith Pro",
            category="copywriting",
            base_price_minor=38000,   # $380
            min_price_minor=26000,    # $260
            concession_rate=0.10,
            rating=4.8,
            turnaround_days=5,
            verified=True,
            persona="Award-winning copywriters for tech and finance brands.",
        ),
        Provider(
            id=4,
            name="ContentHive",
            category="copywriting",
            base_price_minor=18000,   # $180
            min_price_minor=12000,    # $120
            concession_rate=0.18,
            rating=3.9,
            turnaround_days=4,
            verified=False,  # intentionally unverified for BLOCKED demo
            persona="High-volume content production at competitive rates.",
        ),
        # --- logo_design ---
        Provider(
            id=5,
            name="BrandForge",
            category="logo_design",
            base_price_minor=25000,   # $250
            min_price_minor=18000,    # $180
            concession_rate=0.10,
            rating=4.9,
            turnaround_days=6,
            verified=True,
            persona="Premium brand identity design with unlimited revisions.",
        ),
        Provider(
            id=6,
            name="LogoRocket",
            category="logo_design",
            base_price_minor=15000,   # $150
            min_price_minor=10000,    # $100
            concession_rate=0.25,
            rating=4.3,
            turnaround_days=3,
            verified=True,
            persona="Affordable logo design with quick delivery.",
        ),
        # --- marketing ---
        Provider(
            id=7,
            name="GrowthLab",
            category="marketing",
            base_price_minor=120000,  # $1200
            min_price_minor=90000,    # $900
            concession_rate=0.08,
            rating=4.7,
            turnaround_days=14,
            verified=True,
            persona="Data-driven digital marketing for scaling startups.",
        ),
        Provider(
            id=8,
            name="SocialBlast",
            category="marketing",
            base_price_minor=60000,   # $600
            min_price_minor=40000,    # $400
            concession_rate=0.20,
            rating=4.2,
            turnaround_days=10,
            verified=True,
            persona="Social media marketing and paid ads management.",
        ),
    ]
    for p in providers:
        db.add(p)
    db.commit()

    # ── Demo goals ───────────────────────────────────────────────────────────
    #
    # Goal 1 → APPROVED: healthy budget, verified providers, low risk
    # Goal 2 → REVIEW:   moderate budget, single vendor dominates spend (>70%)
    # Goal 3 → BLOCKED:  uses unverified provider (ContentHive)
    #

    goal1 = Goal(
        id=1,
        user_id=1,
        raw_text=(
            "Build a professional website and write compelling copy for my SaaS product. "
            "I need it in 3 weeks and want great quality."
        ),
        budget_minor=200000,  # $2000 — plenty of room
        currency="USD",
        status="NEW",
        trace=[],
    )

    goal2 = Goal(
        id=2,
        user_id=1,
        raw_text=(
            "Design a logo for my new brand. Keep it simple and affordable."
        ),
        budget_minor=20000,   # $200 — tight, one vendor will dominate
        currency="USD",
        status="NEW",
        trace=[],
    )

    goal3 = Goal(
        id=3,
        user_id=1,
        raw_text=(
            "Write content and blog posts for my marketing campaign. "
            "Need stuff written fast and cheap."
        ),
        budget_minor=25000,   # $250 — will route to unverified ContentHive
        currency="USD",
        status="NEW",
        trace=[],
    )

    for g in [goal1, goal2, goal3]:
        db.add(g)
    db.commit()

    print("✅ Seed complete!")
    print(f"   User:      {user.name} <{user.email}>")
    print(f"   Providers: {len(providers)}")
    print(f"   Goals:     3 (IDs 1–3)")
    print()
    print("Demo goals:")
    print("  Goal 1 (ID=1): $2000 budget — expected outcome: APPROVED")
    print("  Goal 2 (ID=2): $200 budget  — expected outcome: REVIEW (vendor concentration)")
    print("  Goal 3 (ID=3): $250 budget  — expected outcome: BLOCKED (unverified provider)")

finally:
    db.close()
