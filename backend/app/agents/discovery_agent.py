"""Discovery Agent: filters and ranks candidate providers per need and reports coverage.

Pure functions: no DB writes, no trace writes.
Verification is never a preference filter and is never relaxed by retries.
"""

from app.config import settings
from app.enums import Scenario
from app.schemas import CoverageReport, Filters, Need, ProviderOut


def initial_filters(scenario: str | None) -> Filters:
    """Return initial preference filters for a goal scenario."""
    if scenario == Scenario.RETRY or scenario == "retry":
        return Filters(min_rating=4.5, max_turnaround_days=5)
    return Filters()


def relax_filters(filters: Filters, attempt: int) -> tuple[Filters, list[str]]:
    """Relax preference filters on discovery retry.

    Attempt 1 drops min_rating; attempt 2 drops max_turnaround_days (and min_rating).
    Verification is never relaxed.
    """
    relaxed: list[str] = []
    new_min_rating = filters.min_rating
    new_max_turnaround = filters.max_turnaround_days
    new_price_ceiling = filters.price_ceiling_minor

    if attempt == 1:
        new_min_rating = None
        relaxed.append("min_rating")
    elif attempt >= 2:
        if new_min_rating is not None:
            new_min_rating = None
            relaxed.append("min_rating")
        new_max_turnaround = None
        relaxed.append("max_turnaround_days")
        if attempt > 2 and new_price_ceiling is not None:
            new_price_ceiling = None
            relaxed.append("price_ceiling_minor")

    return (
        Filters(
            min_rating=new_min_rating,
            max_turnaround_days=new_max_turnaround,
            price_ceiling_minor=new_price_ceiling,
        ),
        relaxed,
    )


def _matches_filters(
    provider: ProviderOut,
    category: str,
    filters: Filters,
    *,
    include_unverified: bool,
) -> bool:
    if provider.category.strip().lower() != category.strip().lower():
        return False
    if not include_unverified and not provider.verified:
        return False
    if filters.min_rating is not None and provider.rating < filters.min_rating:
        return False
    if (
        filters.max_turnaround_days is not None
        and provider.turnaround_days > filters.max_turnaround_days
    ):
        return False
    if (
        filters.price_ceiling_minor is not None
        and provider.base_price_minor > filters.price_ceiling_minor
    ):
        return False
    return True


def run(
    providers: list[ProviderOut],
    needs: list[Need],
    filters: Filters,
    *,
    include_unverified: bool = False,
) -> tuple[dict[str, list[ProviderOut]], CoverageReport]:
    """Filter and rank candidate providers per need, returning candidates and verified coverage."""
    candidates: dict[str, list[ProviderOut]] = {}
    counts: dict[str, int] = {}

    for need in needs:
        matched = [
            p
            for p in providers
            if _matches_filters(p, need.category, filters, include_unverified=include_unverified)
        ]
        matched.sort(key=lambda p: (-p.rating, p.base_price_minor, p.id))
        candidates[need.key] = matched
        counts[need.key] = sum(1 for p in matched if p.verified)

    required = settings.REQUIRED_COVERAGE
    sufficient = bool(needs) and all(c >= required for c in counts.values())
    minimum_met = bool(needs) and all(c >= settings.MIN_COVERAGE for c in counts.values())

    report = CoverageReport(
        counts=counts,
        required=required,
        sufficient=sufficient,
        minimum_met=minimum_met,
    )
    return candidates, report
