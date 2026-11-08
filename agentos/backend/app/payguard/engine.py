"""
app/payguard/engine.py — combines risk.py (AI layer) and policy.py (rules layer)
into a final verdict (FULLY IMPLEMENTED).

Verdict logic:
  - Any BLOCK rule that failed → BLOCKED
  - Any REVIEW rule that failed → REVIEW  (but only if not already BLOCKED)
  - Otherwise → APPROVED

The AI layer can only make the verdict STRICTER:
  - If risk_score is None, verdict is capped at REVIEW (never APPROVED)
  - If risk_score >= 80, the AI_RISK_HIGH rule fires as BLOCK
  - If risk_score >= 50, the AI_RISK_MEDIUM rule fires as REVIEW
  - A policy BLOCK can NEVER be overridden to APPROVED by the AI layer
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.payguard.policy import run_all_rules
from app.payguard.risk import RiskFlag, assess_risk
from app.schemas import PayGuardResult, PayGuardRuleResult


def _derive_verdict(rules: list[PayGuardRuleResult], risk_score: int | None) -> str:
    has_block = any(r.severity == "BLOCK" and not r.passed for r in rules)
    has_review = any(r.severity == "REVIEW" and not r.passed for r in rules)

    if has_block:
        return "BLOCKED"
    if has_review or risk_score is None:
        return "REVIEW"
    return "APPROVED"


def run_payguard(
    plan_id: int,
    items: list[dict[str, Any]],
    plan_total: int,
    plan_currency: str,
    budget_minor: int,
    goal_text: str,
    db: Session,
) -> PayGuardResult:
    """
    Run the full PayGuard check and return a structured result.
    This is the ONLY function callers should use from outside this module.
    """
    # Layer 1: AI risk assessment
    risk = assess_risk(items, goal_text, budget_minor)

    # Layer 2: deterministic policy rules
    rules = run_all_rules(
        plan_id=plan_id,
        items=items,
        plan_total=plan_total,
        plan_currency=plan_currency,
        budget_minor=budget_minor,
        risk_score=risk.risk_score,
        db=db,
    )

    verdict = _derive_verdict(rules, risk.risk_score)

    return PayGuardResult(
        verdict=verdict,
        rules=rules,
        risk_score=risk.risk_score,
        flags=[f.value for f in risk.flags],
        summary=risk.summary,
    )
