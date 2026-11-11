"""PayGuard engine: combines deterministic policy rules with AI risk assessment."""

from __future__ import annotations

import math
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.enums import ErrorCode, RuleId, RuleOutcome, Verdict
from app.errors import ApiError
from app.models import Goal, Plan, Provider
from app.payguard import policy, risk
from app.schemas import Flag, PayGuardResult, PlanDraft, PlanItem, ProviderOut, RuleResult

_AI_RULE_IDS = {RuleId.AI_RISK_HIGH.value, RuleId.AI_RISK_MEDIUM.value}
_UNAVAILABLE_DETAIL = "AI risk check unavailable"


def _build_ai_rules(risk_score: float | None, ai_ok: bool) -> tuple[RuleResult, RuleResult, float | None, bool]:
    if not ai_ok or risk_score is None:
        return (
            RuleResult(id=RuleId.AI_RISK_HIGH, result=RuleOutcome.REVIEW, detail=_UNAVAILABLE_DETAIL),
            RuleResult(id=RuleId.AI_RISK_MEDIUM, result=RuleOutcome.REVIEW, detail=_UNAVAILABLE_DETAIL),
            None,
            False,
        )
    try:
        raw = float(risk_score)
    except (TypeError, ValueError):
        return (
            RuleResult(id=RuleId.AI_RISK_HIGH, result=RuleOutcome.REVIEW, detail=_UNAVAILABLE_DETAIL),
            RuleResult(id=RuleId.AI_RISK_MEDIUM, result=RuleOutcome.REVIEW, detail=_UNAVAILABLE_DETAIL),
            None,
            False,
        )
    if math.isnan(raw) or math.isinf(raw):
        return (
            RuleResult(id=RuleId.AI_RISK_HIGH, result=RuleOutcome.REVIEW, detail=_UNAVAILABLE_DETAIL),
            RuleResult(id=RuleId.AI_RISK_MEDIUM, result=RuleOutcome.REVIEW, detail=_UNAVAILABLE_DETAIL),
            None,
            False,
        )

    score = max(0.0, min(1.0, raw))
    high_thresh = settings.HIGH_RISK_THRESHOLD
    med_thresh = settings.MEDIUM_RISK_THRESHOLD

    if score >= high_thresh:
        high_rule = RuleResult(
            id=RuleId.AI_RISK_HIGH,
            result=RuleOutcome.BLOCK,
            detail=f"AI risk score {score:.2f} >= high threshold {high_thresh}",
        )
    else:
        high_rule = RuleResult(
            id=RuleId.AI_RISK_HIGH,
            result=RuleOutcome.PASS,
            detail=f"AI risk score {score:.2f} < high threshold {high_thresh}",
        )

    if score >= med_thresh:
        med_rule = RuleResult(
            id=RuleId.AI_RISK_MEDIUM,
            result=RuleOutcome.REVIEW,
            detail=f"AI risk score {score:.2f} >= medium threshold {med_thresh}",
        )
    else:
        med_rule = RuleResult(
            id=RuleId.AI_RISK_MEDIUM,
            result=RuleOutcome.PASS,
            detail=f"AI risk score {score:.2f} < medium threshold {med_thresh}",
        )

    return high_rule, med_rule, score, True


def combine(
    policy_results: list[RuleResult],
    risk_score: float | None,
    ai_flags: list[Flag],
    ai_ok: bool,
) -> PayGuardResult:
    """Combine 8 policy RuleResults and AI risk outputs into a PayGuardResult.

    - Outputs all 10 rules in RuleId enum order.
    - Deterministic BLOCK always produces Verdict.BLOCKED; AI can never downgrade a BLOCK.
    - If ai_ok is False, AI_RISK_HIGH and AI_RISK_MEDIUM are both REVIEW ("AI risk check unavailable"),
      capping the verdict at REVIEW (unless a rule BLOCKs).
    """
    high_rule, med_rule, clean_score, effective_ai_ok = _build_ai_rules(risk_score, ai_ok)

    by_id: dict[str, RuleResult] = {r.id: r for r in policy_results}
    by_id[RuleId.AI_RISK_HIGH.value] = high_rule
    by_id[RuleId.AI_RISK_MEDIUM.value] = med_rule

    ordered_rules: list[RuleResult] = [by_id[rid.value] for rid in RuleId if rid.value in by_id]

    flags: list[Flag] = []
    seen_flag_ids: set[str] = set()
    for rule in ordered_rules:
        if rule.result in (RuleOutcome.REVIEW, RuleOutcome.BLOCK):
            source = "AI" if rule.id in _AI_RULE_IDS else "POLICY"
            flags.append(
                Flag(
                    id=rule.id,
                    source=source,
                    message=rule.detail,
                    requires_ack=(rule.result == RuleOutcome.REVIEW),
                )
            )
            seen_flag_ids.add(rule.id)

    for af in ai_flags:
        fid = af.id if af.id.startswith("AI:") else f"AI:{af.id}"
        if fid not in seen_flag_ids:
            flags.append(
                Flag(
                    id=fid,
                    source="AI",
                    message=af.message,
                    requires_ack=False,
                )
            )
            seen_flag_ids.add(fid)

    if any(r.result == RuleOutcome.BLOCK for r in ordered_rules):
        verdict = Verdict.BLOCKED
    elif any(r.result == RuleOutcome.REVIEW for r in ordered_rules) or not effective_ai_ok:
        verdict = Verdict.REVIEW
    else:
        verdict = Verdict.APPROVED

    return PayGuardResult(
        verdict=verdict,
        risk_score=clean_score,
        ai_ok=effective_ai_ok,
        flags=flags,
        rules=ordered_rules,
        checked_at=datetime.now(UTC),
    )


def run_payguard(
    plan: PlanDraft,
    goal_budget_minor: int,
    goal_currency: str,
    goal_text: str,
    providers: dict[int, ProviderOut],
    other_plan_statuses: list[str],
) -> PayGuardResult:
    """Run deterministic policy evaluation and AI risk assessment, then combine."""
    policy_results = policy.evaluate(
        plan=plan,
        goal_budget_minor=goal_budget_minor,
        goal_currency=goal_currency,
        providers=providers,
        other_plan_statuses=other_plan_statuses,
    )
    risk_score, ai_flags, ai_ok = risk.assess(
        plan=plan,
        goal_text=goal_text,
        budget_minor=goal_budget_minor,
    )
    return combine(policy_results, risk_score, ai_flags, ai_ok)


def run_for_plan(db: Session, plan_id: int) -> PayGuardResult:
    """Load Plan, Goal, referenced Providers, and other plans' statuses from DB; evaluate PayGuard.

    Uses stored plan.total_minor (NOT a recomputed sum) so TOTAL_INTEGRITY detects tampering.
    Does NOT commit.
    """
    plan_row = db.get(Plan, plan_id)
    if plan_row is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Plan {plan_id} not found")

    goal_row = db.get(Goal, plan_row.goal_id)
    if goal_row is None:
        raise ApiError(ErrorCode.NOT_FOUND, f"Goal {plan_row.goal_id} not found")

    items = [PlanItem.model_validate(raw) for raw in (plan_row.items or [])]
    provider_ids = {item.provider_id for item in items}

    providers: dict[int, ProviderOut] = {}
    if provider_ids:
        prov_rows = db.query(Provider).filter(Provider.id.in_(provider_ids)).all()
        providers = {p.id: ProviderOut.model_validate(p) for p in prov_rows}

    other_plans = (
        db.query(Plan)
        .filter(Plan.goal_id == plan_row.goal_id, Plan.id != plan_row.id)
        .all()
    )
    other_statuses = [p.status for p in other_plans]

    draft = PlanDraft(
        items=items,
        total_minor=plan_row.total_minor,
        currency=plan_row.currency,
        rationale=plan_row.rationale or "",
    )

    return run_payguard(
        plan=draft,
        goal_budget_minor=goal_row.budget_minor,
        goal_currency=goal_row.currency,
        goal_text=goal_row.raw_text,
        providers=providers,
        other_plan_statuses=other_statuses,
    )
