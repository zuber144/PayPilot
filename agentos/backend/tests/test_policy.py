"""
tests/test_policy.py — unit tests for the PayGuard policy engine.

Tests:
1. over_budget          → BUDGET_CAP fails → BLOCKED
2. unverified_provider  → VERIFIED_PROVIDER fails → BLOCKED
3. price_below_floor    → PRICE_FLOOR fails → BLOCKED
4. duplicate_payment    → NO_DUPLICATE fails → BLOCKED
5. clean_plan           → all rules pass → APPROVED
"""
from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models import Transaction
from app.payguard.engine import run_payguard
from app.payguard.policy import (
    rule_budget_cap,
    rule_no_duplicate,
    rule_price_floor,
    rule_verified_provider,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_items(provider_id: int, price_minor: int) -> list[dict]:
    return [
        {
            "need_key": "web_design",
            "provider_id": provider_id,
            "provider_name": "Test Provider",
            "price_minor": price_minor,
            "scope": "Full website",
            "timeline_days": 7,
            "offer_id": 1,
        }
    ]


# ---------------------------------------------------------------------------
# 1. Over budget
# ---------------------------------------------------------------------------

def test_budget_cap_fails_when_over_budget():
    result = rule_budget_cap(plan_total=150000, budget_minor=100000)
    assert not result.passed
    assert result.severity == "BLOCK"
    assert result.rule == "BUDGET_CAP"


def test_budget_cap_passes_when_under_budget():
    result = rule_budget_cap(plan_total=90000, budget_minor=100000)
    assert result.passed


def test_over_budget_plan_is_blocked(db, demo_goal, verified_provider):
    from app.models import Plan

    # Plan total exceeds goal budget
    plan = Plan(
        goal_id=demo_goal.id,
        items=_make_items(verified_provider.id, 150000),
        total_minor=150000,  # > budget_minor=100000
        currency="USD",
        rationale="Test",
        status="DRAFT",
    )
    db.add(plan)
    db.commit()

    result = run_payguard(
        plan_id=plan.id,
        items=list(plan.items),
        plan_total=plan.total_minor,
        plan_currency=plan.currency,
        budget_minor=demo_goal.budget_minor,
        goal_text=demo_goal.raw_text,
        db=db,
    )
    assert result.verdict == "BLOCKED"
    budget_rule = next(r for r in result.rules if r.rule == "BUDGET_CAP")
    assert not budget_rule.passed


# ---------------------------------------------------------------------------
# 2. Unverified provider
# ---------------------------------------------------------------------------

def test_unverified_provider_fails(db, unverified_provider):
    result = rule_verified_provider(
        items=_make_items(unverified_provider.id, 10000),
        db=db,
    )
    assert not result.passed
    assert result.severity == "BLOCK"


def test_verified_provider_passes(db, verified_provider):
    result = rule_verified_provider(
        items=_make_items(verified_provider.id, 40000),
        db=db,
    )
    assert result.passed


def test_unverified_plan_is_blocked(db, demo_goal, unverified_provider):
    from app.models import Plan

    plan = Plan(
        goal_id=demo_goal.id,
        items=_make_items(unverified_provider.id, 12000),
        total_minor=12000,
        currency="USD",
        rationale="Test",
        status="DRAFT",
    )
    db.add(plan)
    db.commit()

    result = run_payguard(
        plan_id=plan.id,
        items=list(plan.items),
        plan_total=plan.total_minor,
        plan_currency=plan.currency,
        budget_minor=demo_goal.budget_minor,
        goal_text=demo_goal.raw_text,
        db=db,
    )
    assert result.verdict == "BLOCKED"


# ---------------------------------------------------------------------------
# 3. Price below floor
# ---------------------------------------------------------------------------

def test_price_floor_fails(db, verified_provider):
    # min_price_minor=30000; set price below that
    result = rule_price_floor(
        items=_make_items(verified_provider.id, 10000),
        db=db,
    )
    assert not result.passed
    assert result.severity == "BLOCK"


def test_price_floor_passes(db, verified_provider):
    result = rule_price_floor(
        items=_make_items(verified_provider.id, 35000),
        db=db,
    )
    assert result.passed


# ---------------------------------------------------------------------------
# 4. Duplicate payment
# ---------------------------------------------------------------------------

def test_no_duplicate_fails_when_live_transaction_exists(db, draft_plan):
    # Insert a live transaction for the plan
    txn = Transaction(
        plan_id=draft_plan.id,
        paypal_order_id="PP-ORDER-EXISTING-123",
        amount_minor=draft_plan.total_minor,
        currency="USD",
        status="CREATED",
    )
    db.add(txn)
    db.commit()

    result = rule_no_duplicate(plan_id=draft_plan.id, db=db)
    assert not result.passed
    assert result.severity == "BLOCK"


def test_no_duplicate_passes_when_no_transaction(db, draft_plan):
    result = rule_no_duplicate(plan_id=draft_plan.id, db=db)
    assert result.passed


# ---------------------------------------------------------------------------
# 5. Clean plan → APPROVED
# ---------------------------------------------------------------------------

def test_clean_plan_is_approved(db, demo_goal, verified_provider):
    from app.models import Plan, Provider

    prov2 = Provider(
        id=20,
        name="Second Verified Provider",
        category="copywriting",
        base_price_minor=35000,
        min_price_minor=20000,
        concession_rate=0.1,
        rating=4.7,
        turnaround_days=5,
        verified=True,
        persona="Expert copywriter",
    )
    db.add(prov2)
    db.commit()

    items = [
        {
            "need_key": "web_design",
            "provider_id": verified_provider.id,
            "provider_name": verified_provider.name,
            "price_minor": 30000,
            "scope": "Full website",
            "timeline_days": 7,
            "offer_id": 1,
        },
        {
            "need_key": "copywriting",
            "provider_id": prov2.id,
            "provider_name": prov2.name,
            "price_minor": 30000,
            "scope": "All copywriting",
            "timeline_days": 5,
            "offer_id": 2,
        },
    ]

    plan = Plan(
        goal_id=demo_goal.id,
        items=items,
        total_minor=60000,
        currency="USD",
        rationale="Best value",
        status="DRAFT",
    )
    db.add(plan)
    db.commit()

    result = run_payguard(
        plan_id=plan.id,
        items=list(plan.items),
        plan_total=plan.total_minor,
        plan_currency=plan.currency,
        budget_minor=demo_goal.budget_minor,
        goal_text=demo_goal.raw_text,
        db=db,
    )
    assert result.verdict == "APPROVED"
    assert all(r.passed for r in result.rules if r.severity == "BLOCK")
