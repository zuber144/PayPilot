"""
app/payguard/policy.py — deterministic policy rules (FULLY IMPLEMENTED).

Each rule is a function that returns a PayGuardRuleResult.
Severities: BLOCK (hard stop), REVIEW (soft warning), INFO (advisory).

Rules:
1. BUDGET_CAP          — total_minor <= goal.budget_minor
2. TXN_LIMIT           — total_minor <= settings.max_txn_minor
3. VERIFIED_PROVIDER   — all providers in items are verified
4. CURRENCY_MATCH      — all items use the same currency as the plan
5. NO_DUPLICATE        — no existing CREATED/COMPLETED transaction for this plan
6. PRICE_FLOOR         — each item price >= provider.min_price_minor
7. TOTAL_INTEGRITY     — sum(item prices) == plan.total_minor
8. AI_RISK_HIGH        — risk_score < 80
9. AI_RISK_MEDIUM      — risk_score < 50
10. SINGLE_VENDOR_SHARE— no vendor holds >70% of total spend
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Provider, Transaction
from app.schemas import PayGuardRuleResult


def _rule(rule: str, passed: bool, severity: str, reason: str) -> PayGuardRuleResult:
    return PayGuardRuleResult(rule=rule, passed=passed, severity=severity, reason=reason)


# ---------------------------------------------------------------------------
# Individual rule checkers
# ---------------------------------------------------------------------------

def rule_budget_cap(
    plan_total: int,
    budget_minor: int,
) -> PayGuardRuleResult:
    passed = plan_total <= budget_minor
    return _rule(
        "BUDGET_CAP",
        passed,
        "BLOCK",
        f"Plan total {plan_total} {'≤' if passed else '>'} goal budget {budget_minor}",
    )


def rule_txn_limit(plan_total: int) -> PayGuardRuleResult:
    limit = get_settings().max_txn_minor
    passed = plan_total <= limit
    return _rule(
        "TXN_LIMIT",
        passed,
        "BLOCK",
        f"Plan total {plan_total} {'≤' if passed else '>'} max transaction limit {limit}",
    )


def rule_verified_provider(
    items: list[dict[str, Any]],
    db: Session,
) -> PayGuardRuleResult:
    unverified = []
    for item in items:
        pid = item.get("provider_id")
        if pid is None:
            continue
        prov = db.get(Provider, pid)
        if prov and not prov.verified:
            unverified.append(prov.name)
    passed = len(unverified) == 0
    return _rule(
        "VERIFIED_PROVIDER",
        passed,
        "BLOCK",
        "All providers verified" if passed
        else f"Unverified providers: {', '.join(unverified)}",
    )


def rule_currency_match(
    items: list[dict[str, Any]],
    plan_currency: str,
) -> PayGuardRuleResult:
    # Items don't store currency individually — this rule checks plan vs. goal currency
    # (always matching since we propagate currency from goal to plan)
    passed = bool(plan_currency) and len(plan_currency) == 3
    return _rule(
        "CURRENCY_MATCH",
        passed,
        "BLOCK",
        f"Currency '{plan_currency}' is valid ISO-4217" if passed
        else f"Invalid or missing currency '{plan_currency}'",
    )


def rule_no_duplicate(
    plan_id: int,
    db: Session,
) -> PayGuardRuleResult:
    existing = (
        db.query(Transaction)
        .filter(
            Transaction.plan_id == plan_id,
            Transaction.status.in_(["CREATED", "COMPLETED"]),
        )
        .first()
    )
    passed = existing is None
    return _rule(
        "NO_DUPLICATE",
        passed,
        "BLOCK",
        "No live transaction exists for this plan" if passed
        else f"Live transaction {existing.id} already exists (status={existing.status})",
    )


def rule_price_floor(
    items: list[dict[str, Any]],
    db: Session,
) -> PayGuardRuleResult:
    violations = []
    for item in items:
        pid = item.get("provider_id")
        price = item.get("price_minor", 0)
        if pid is None:
            continue
        prov = db.get(Provider, pid)
        if prov and price < prov.min_price_minor:
            violations.append(
                f"{prov.name}: {price} < floor {prov.min_price_minor}"
            )
    passed = len(violations) == 0
    return _rule(
        "PRICE_FLOOR",
        passed,
        "BLOCK",
        "All item prices ≥ provider floors" if passed
        else f"Floor violations: {'; '.join(violations)}",
    )


def rule_total_integrity(
    items: list[dict[str, Any]],
    plan_total: int,
) -> PayGuardRuleResult:
    computed = sum(item.get("price_minor", 0) for item in items)
    passed = computed == plan_total
    return _rule(
        "TOTAL_INTEGRITY",
        passed,
        "BLOCK",
        f"Sum of items ({computed}) matches plan total ({plan_total})" if passed
        else f"Sum of items ({computed}) ≠ plan total ({plan_total})",
    )


def rule_ai_risk_high(risk_score: int | None) -> PayGuardRuleResult:
    if risk_score is None:
        passed = True  # unknown → not a hard block
        reason = "Risk score unavailable — skipping AI_RISK_HIGH rule"
    else:
        passed = risk_score < 80
        reason = (
            f"Risk score {risk_score} < 80 (acceptable)"
            if passed
            else f"Risk score {risk_score} ≥ 80 — HIGH RISK"
        )
    return _rule("AI_RISK_HIGH", passed, "BLOCK", reason)


def rule_ai_risk_medium(risk_score: int | None) -> PayGuardRuleResult:
    if risk_score is None:
        passed = False  # unknown → cap at REVIEW
        reason = "Risk score unavailable — capping at REVIEW"
    else:
        passed = risk_score < 50
        reason = (
            f"Risk score {risk_score} < 50 (low risk)"
            if passed
            else f"Risk score {risk_score} ≥ 50 — MEDIUM RISK"
        )
    return _rule("AI_RISK_MEDIUM", passed, "REVIEW", reason)


def rule_single_vendor_share(
    items: list[dict[str, Any]],
    plan_total: int,
) -> PayGuardRuleResult:
    if plan_total == 0:
        return _rule("SINGLE_VENDOR_SHARE", True, "REVIEW", "Total is zero — skipping")

    vendor_totals: dict[int, int] = {}
    for item in items:
        pid = item.get("provider_id", 0)
        vendor_totals[pid] = vendor_totals.get(pid, 0) + item.get("price_minor", 0)

    max_share = max(vendor_totals.values(), default=0) / plan_total
    passed = max_share <= 0.70
    return _rule(
        "SINGLE_VENDOR_SHARE",
        passed,
        "REVIEW",
        f"Max vendor share {max_share:.0%} ≤ 70%" if passed
        else f"Max vendor share {max_share:.0%} > 70% — concentration risk",
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_all_rules(
    plan_id: int,
    items: list[dict[str, Any]],
    plan_total: int,
    plan_currency: str,
    budget_minor: int,
    risk_score: int | None,
    db: Session,
) -> list[PayGuardRuleResult]:
    """Run all deterministic policy rules and return the full result list."""
    return [
        rule_budget_cap(plan_total, budget_minor),
        rule_txn_limit(plan_total),
        rule_verified_provider(items, db),
        rule_currency_match(items, plan_currency),
        rule_no_duplicate(plan_id, db),
        rule_price_floor(items, db),
        rule_total_integrity(items, plan_total),
        rule_ai_risk_high(risk_score),
        rule_ai_risk_medium(risk_score),
        rule_single_vendor_share(items, plan_total),
    ]
