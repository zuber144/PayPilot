"""Deterministic PayGuard policy rules (pure functions, no DB or LLM access)."""

from __future__ import annotations

from app.config import settings
from app.enums import PlanStatus, RuleId, RuleOutcome
from app.schemas import PlanDraft, ProviderOut, RuleResult

_DUPLICATE_STATUSES = {PlanStatus.PAYING.value, PlanStatus.PAID.value}


def _check_budget_cap(plan: PlanDraft, goal_budget_minor: int) -> RuleResult:
    if not plan.items or plan.total_minor <= 0:
        return RuleResult(
            id=RuleId.BUDGET_CAP,
            result=RuleOutcome.BLOCK,
            detail=(
                "Plan must have at least one item and a positive total "
                f"(items={len(plan.items)}, total={plan.total_minor})"
            ),
        )
    if goal_budget_minor <= 0 or plan.total_minor > goal_budget_minor:
        return RuleResult(
            id=RuleId.BUDGET_CAP,
            result=RuleOutcome.BLOCK,
            detail=f"Plan total {plan.total_minor} exceeds goal budget {goal_budget_minor}",
        )
    return RuleResult(
        id=RuleId.BUDGET_CAP,
        result=RuleOutcome.PASS,
        detail=f"Plan total {plan.total_minor} is within goal budget {goal_budget_minor}",
    )


def _check_txn_limit(plan: PlanDraft) -> RuleResult:
    limit = settings.MAX_TXN_MINOR
    if plan.total_minor > limit:
        return RuleResult(
            id=RuleId.TXN_LIMIT,
            result=RuleOutcome.BLOCK,
            detail=f"Plan total {plan.total_minor} exceeds transaction limit {limit}",
        )
    return RuleResult(
        id=RuleId.TXN_LIMIT,
        result=RuleOutcome.PASS,
        detail=f"Plan total {plan.total_minor} is within transaction limit {limit}",
    )


def _check_verified_provider(plan: PlanDraft, providers: dict[int, ProviderOut]) -> RuleResult:
    if not plan.items:
        return RuleResult(
            id=RuleId.VERIFIED_PROVIDER,
            result=RuleOutcome.BLOCK,
            detail="Plan has no items; cannot verify providers",
        )
    unknown: list[int] = []
    unverified: list[str] = []
    for item in plan.items:
        prov = providers.get(item.provider_id)
        if prov is None:
            unknown.append(item.provider_id)
        elif not prov.verified:
            unverified.append(f"{prov.name} (id={prov.id})")

    if unknown or unverified:
        parts: list[str] = []
        if unknown:
            parts.append(f"unknown provider id(s): {unknown}")
        if unverified:
            parts.append(f"unverified provider(s): {', '.join(unverified)}")
        return RuleResult(
            id=RuleId.VERIFIED_PROVIDER,
            result=RuleOutcome.BLOCK,
            detail="Provider verification failed: " + "; ".join(parts),
        )
    return RuleResult(
        id=RuleId.VERIFIED_PROVIDER,
        result=RuleOutcome.PASS,
        detail="All selected sellers are verified (allowlisted store, rating and review thresholds)",
    )


def _check_currency_match(plan: PlanDraft, goal_currency: str) -> RuleResult:
    supported = settings.SUPPORTED_CURRENCIES
    if goal_currency not in supported:
        return RuleResult(
            id=RuleId.CURRENCY_MATCH,
            result=RuleOutcome.BLOCK,
            detail=f"Goal currency '{goal_currency}' is not in supported currencies {supported}",
        )
    if plan.currency != goal_currency:
        return RuleResult(
            id=RuleId.CURRENCY_MATCH,
            result=RuleOutcome.BLOCK,
            detail=f"Plan currency '{plan.currency}' does not match goal currency '{goal_currency}'",
        )
    mismatched = [
        f"{item.need_key}:{item.currency}" for item in plan.items if item.currency != goal_currency
    ]
    if mismatched:
        return RuleResult(
            id=RuleId.CURRENCY_MATCH,
            result=RuleOutcome.BLOCK,
            detail=f"Item currency mismatch against '{goal_currency}': {', '.join(mismatched)}",
        )
    return RuleResult(
        id=RuleId.CURRENCY_MATCH,
        result=RuleOutcome.PASS,
        detail=f"All items and plan match supported goal currency {goal_currency}",
    )


def _check_no_duplicate(other_plan_statuses: list[str]) -> RuleResult:
    active = [str(s) for s in other_plan_statuses if str(s) in _DUPLICATE_STATUSES]
    if active:
        return RuleResult(
            id=RuleId.NO_DUPLICATE,
            result=RuleOutcome.BLOCK,
            detail=f"Another plan for this goal is already in payment state: {', '.join(active)}",
        )
    return RuleResult(
        id=RuleId.NO_DUPLICATE,
        result=RuleOutcome.PASS,
        detail="No other plan for this goal is PAYING or PAID",
    )


def _check_price_floor(plan: PlanDraft, providers: dict[int, ProviderOut]) -> RuleResult:
    """Listing price integrity (rule id PRICE_FLOOR kept for the contract): every line must equal
    packs * stored pack price + stored shipping, with packs >= 1 and pack price >= the listing floor.
    Catches any tampering or drift between the plan and the persisted listing."""
    if not plan.items:
        return RuleResult(
            id=RuleId.PRICE_FLOOR,
            result=RuleOutcome.BLOCK,
            detail="Plan has no items; cannot check listing prices",
        )
    violations: list[str] = []
    for item in plan.items:
        prov = providers.get(item.provider_id)
        if prov is None:
            violations.append(f"unknown listing id={item.provider_id} for {item.need_key}")
            continue
        if item.packs < 1:
            violations.append(f"{prov.name} ({item.need_key}): packs {item.packs} < 1")
            continue
        if prov.base_price_minor < prov.min_price_minor:
            violations.append(
                f"{prov.name} ({item.need_key}): pack price {prov.base_price_minor} < floor {prov.min_price_minor}"
            )
        expected = item.packs * prov.base_price_minor + prov.shipping_minor
        if item.price_minor != expected:
            violations.append(
                f"{prov.name} ({item.need_key}): line price {item.price_minor} != "
                f"{item.packs} x {prov.base_price_minor} + shipping {prov.shipping_minor} = {expected}"
            )
    if violations:
        return RuleResult(
            id=RuleId.PRICE_FLOOR,
            result=RuleOutcome.BLOCK,
            detail="Listing price mismatch: " + "; ".join(violations),
        )
    return RuleResult(
        id=RuleId.PRICE_FLOOR,
        result=RuleOutcome.PASS,
        detail="Every line equals packs x listing price + shipping",
    )


def _check_total_integrity(plan: PlanDraft) -> RuleResult:
    if not plan.items or plan.total_minor <= 0:
        return RuleResult(
            id=RuleId.TOTAL_INTEGRITY,
            result=RuleOutcome.BLOCK,
            detail=f"Plan must have items and a positive total (items={len(plan.items)}, total={plan.total_minor})",
        )
    if any(item.price_minor <= 0 for item in plan.items):
        return RuleResult(
            id=RuleId.TOTAL_INTEGRITY,
            result=RuleOutcome.BLOCK,
            detail="Every plan item must have a positive price_minor",
        )
    items_sum = sum(item.price_minor for item in plan.items)
    if plan.total_minor != items_sum:
        return RuleResult(
            id=RuleId.TOTAL_INTEGRITY,
            result=RuleOutcome.BLOCK,
            detail=f"Plan total {plan.total_minor} does not equal sum of line items {items_sum}",
        )
    return RuleResult(
        id=RuleId.TOTAL_INTEGRITY,
        result=RuleOutcome.PASS,
        detail=f"Plan total {plan.total_minor} matches sum of {len(plan.items)} item(s)",
    )


def _check_single_vendor_share(plan: PlanDraft) -> RuleResult:
    if not plan.items or plan.total_minor <= 0:
        return RuleResult(
            id=RuleId.SINGLE_VENDOR_SHARE,
            result=RuleOutcome.PASS,
            detail="No vendor share violation on empty/zero plan",
        )
    vendor_sums: dict[int, int] = {}
    vendor_names: dict[int, str] = {}
    for item in plan.items:
        vendor_sums[item.provider_id] = vendor_sums.get(item.provider_id, 0) + item.price_minor
        vendor_names[item.provider_id] = item.provider_name

    # Integer-safe comparison in basis points (e.g. 0.70 -> 7000 bps: provider_sum * 10000 > total * 7000)
    scale = 10_000
    max_bps = round(settings.SINGLE_VENDOR_SHARE_MAX * scale)
    total = plan.total_minor

    exceeded: list[str] = []
    for pid, vsum in vendor_sums.items():
        if vsum * scale > total * max_bps:
            pct = (vsum * 100) // total
            exceeded.append(f"{vendor_names.get(pid, f'provider {pid}')} ({pct}%)")

    if exceeded:
        max_pct = round(settings.SINGLE_VENDOR_SHARE_MAX * 100)
        return RuleResult(
            id=RuleId.SINGLE_VENDOR_SHARE,
            result=RuleOutcome.REVIEW,
            detail=f"Vendor concentration exceeds {max_pct}% threshold: {', '.join(exceeded)}",
        )
    return RuleResult(
        id=RuleId.SINGLE_VENDOR_SHARE,
        result=RuleOutcome.PASS,
        detail="No single vendor exceeds the maximum share threshold",
    )


def evaluate(
    plan: PlanDraft,
    goal_budget_minor: int,
    goal_currency: str,
    providers: dict[int, ProviderOut],
    other_plan_statuses: list[str],
) -> list[RuleResult]:
    """Evaluate the 8 deterministic PayGuard rules in RuleId enum order."""
    return [
        _check_budget_cap(plan, goal_budget_minor),
        _check_txn_limit(plan),
        _check_verified_provider(plan, providers),
        _check_currency_match(plan, goal_currency),
        _check_no_duplicate(other_plan_statuses),
        _check_price_floor(plan, providers),
        _check_total_integrity(plan),
        _check_single_vendor_share(plan),
    ]
