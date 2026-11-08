"""
tests/conftest.py — shared fixtures for the test suite.
"""
from __future__ import annotations

import os

TEST_DB_URL = "sqlite:///./test.db"
os.environ["DATABASE_URL"] = TEST_DB_URL

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.config
app.config.get_settings.cache_clear()

import app.db
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
app.db.engine = test_engine
app.db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

from app.db import Base, get_db
from app.main import app
from app.models import Goal, Plan, Provider, Transaction, User
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db():
    """Fresh DB session with all tables created and dropped after each test."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db):
    """FastAPI test client with the test DB injected."""
    def override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def demo_user(db):
    user = User(id=1, name="Test User", email="test@example.com")
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def verified_provider(db):
    prov = Provider(
        id=10,
        name="Good Provider",
        category="web_design",
        base_price_minor=50000,
        min_price_minor=30000,
        concession_rate=0.15,
        rating=4.5,
        turnaround_days=7,
        verified=True,
        persona="A solid verified provider.",
    )
    db.add(prov)
    db.commit()
    return prov


@pytest.fixture
def unverified_provider(db):
    prov = Provider(
        id=11,
        name="Sketchy Provider",
        category="copywriting",
        base_price_minor=15000,
        min_price_minor=10000,
        concession_rate=0.20,
        rating=3.5,
        turnaround_days=3,
        verified=False,
        persona="Cheap and fast, but not verified.",
    )
    db.add(prov)
    db.commit()
    return prov


@pytest.fixture
def demo_goal(db, demo_user):
    goal = Goal(
        id=100,
        user_id=1,
        raw_text="Build a website",
        budget_minor=100000,
        currency="USD",
        status="NEW",
        trace=[],
    )
    db.add(goal)
    db.commit()
    return goal


@pytest.fixture
def draft_plan(db, demo_goal, verified_provider):
    plan = Plan(
        id=200,
        goal_id=demo_goal.id,
        items=[
            {
                "need_key": "web_design",
                "provider_id": verified_provider.id,
                "provider_name": verified_provider.name,
                "price_minor": 40000,
                "scope": "Full website",
                "timeline_days": 7,
                "offer_id": 1,
            }
        ],
        total_minor=40000,
        currency="USD",
        rationale="Best value for the budget.",
        status="DRAFT",
    )
    db.add(plan)
    db.commit()
    return plan
