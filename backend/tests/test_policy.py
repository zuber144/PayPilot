"""Tests for PayGuard deterministic policy rules (app.payguard.policy)."""

from app.enums import PlanStatus, RuleId, RuleOutcome
from app.payguard import policy
from app.schemas import PlanDraft, PlanItem, ProviderOut


def _providers() -> dict[int, ProviderOut]:
    return {
        1: ProviderOut(
            id=1,
            name="ABC Catering",
            category="catering",
            base_price_minor=2_800_000,
            min_price_minor=2_400_000,
            concession_rate=0.0375,
            rating=4.6,
            turnaround_days=7,
            verified=True,
            currency="USD",
        ),
        2: ProviderOut(
            id=2,
            name="Studio X",
            category="photography",
            base_price_minor=1_800_000,
            min_price_minor=1_500_000,
            concession_rate=0.0385,
            rating=4.7,
            turnaround_days=4,
            verified=True,
            currency="USD",
        ),
        3: ProviderOut(
            id=3,
            name="PixelNest",
            category="photography",
            base_price_minor=1_400_000,
            min_price_minor=1_200_000,
            concession_rate=0.04,
            rating=4.5,
            turnaround_days=3,
            verified=False,
            currency="USD",
        ),
    }


def _clean_plan() -> PlanDraft:
    return PlanDraft(
        items=[
            PlanItem(
                need_key="catering",
                provider_id=1,
                provider_name="ABC Catering",
                price_minor=2_500_000,
                timeline_days=7,
                verified=True,
                currency="USD",
            ),
            PlanItem(
                need_key="photography",
                provider_id=2,
                provider_name="Studio X",
                price_minor=1_600_000,
                timeline_days=4,
                verified=True,
                currency="USD",
            ),
        ],
        total_minor=4_100_000,
        currency="USD",
        rationale="Balanced selection within budget.",
    )


def test_verified_provider_failure_blocks() -> None:
    """Section 15 #3: Provider verification failure —
    Unverified providers cannot pass the mandatory policy (VERIFIED_PROVIDER -> BLOCK).
    """
    plan = PlanDraft(
        items=[
            PlanItem(
                need_key="catering",
                provider_id=1,
                provider_name="ABC Catering",
                price_minor=2_400_000,
                timeline_days=7,
                verified=True,
                currency="USD",
            ),
            PlanItem(
                need_key="photography",
                provider_id=3,
                provider_name="PixelNest",
                price_minor=1_200_000,
                timeline_days=3,
                verified=False,
                currency="USD",
            ),
        ],
        total_minor=3_600_000,
        currency="USD",
    )
    results = policy.evaluate(plan, 5_000_000, "USD", _providers(), [])
    by_id = {r.id: r.result for r in results}
    assert by_id[RuleId.VERIFIED_PROVIDER] == RuleOutcome.BLOCK


def test_over_budget_plan_blocks() -> None:
    """Section 15 #4: Over-budget plan —
    Budget policy blocks the purchase when plan total > goal budget (BUDGET_CAP -> BLOCK).
    """
    plan = _clean_plan()
    results = policy.evaluate(plan, 4_000_000, "USD", _providers(), [])
    by_id = {r.id: r.result for r in results}
    assert by_id[RuleId.BUDGET_CAP] == RuleOutcome.BLOCK


def test_price_below_provider_min_blocks() -> None:
    """Section 15 #5: Price below provider minimum —
    PRICE_FLOOR blocks a plan where an item price is below the provider's min_price_minor.
    """
    plan = _clean_plan()
    plan.items[0].price_minor = 2_000_000  # below ABC Catering min 2,400,000
    plan.total_minor = 3_600_000
    results = policy.evaluate(plan, 5_000_000, "USD", _providers(), [])
    by_id = {r.id: r.result for r in results}
    assert by_id[RuleId.PRICE_FLOOR] == RuleOutcome.BLOCK


def test_plan_total_mismatch_blocks() -> None:
    """Section 15 #6: Plan total mismatch —
    Server-side amount integrity is enforced (TOTAL_INTEGRITY -> BLOCK).
    """
    plan = _clean_plan()
    plan.total_minor = 4_000_000  # items sum to 4,100,000
    results = policy.evaluate(plan, 5_000_000, "USD", _providers(), [])
    by_id = {r.id: r.result for r in results}
    assert by_id[RuleId.TOTAL_INTEGRITY] == RuleOutcome.BLOCK


def test_currency_mismatch_blocks() -> None:
    """Work-division 3.9: Currency mismatch triggers CURRENCY_MATCH -> BLOCK."""
    plan = _clean_plan()
    plan.items[1].currency = "EUR"
    results = policy.evaluate(plan, 5_000_000, "USD", _providers(), [])
    by_id = {r.id: r.result for r in results}
    assert by_id[RuleId.CURRENCY_MATCH] == RuleOutcome.BLOCK


def test_duplicate_plan_blocks() -> None:
    """Work-division 3.9: Existing PAYING or PAID plan triggers NO_DUPLICATE -> BLOCK."""
    plan = _clean_plan()
    results = policy.evaluate(plan, 5_000_000, "USD", _providers(), [PlanStatus.PAID])
    by_id = {r.id: r.result for r in results}
    assert by_id[RuleId.NO_DUPLICATE] == RuleOutcome.BLOCK


def test_single_vendor_share_review() -> None:
    """Single vendor holding > 70% of plan total triggers SINGLE_VENDOR_SHARE -> REVIEW."""
    plan = PlanDraft(
        items=[
            PlanItem(
                need_key="catering",
                provider_id=1,
                provider_name="ABC Catering",
                price_minor=2_500_000,
                timeline_days=7,
                verified=True,
                currency="USD",
            )
        ],
        total_minor=2_500_000,
        currency="USD",
    )
    results = policy.evaluate(plan, 5_000_000, "USD", _providers(), [])
    by_id = {r.id: r.result for r in results}
    assert by_id[RuleId.SINGLE_VENDOR_SHARE] == RuleOutcome.REVIEW
