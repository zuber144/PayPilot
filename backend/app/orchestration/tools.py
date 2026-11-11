"""Permitted orchestrator actions and validation helpers."""

from __future__ import annotations

from collections.abc import Sequence

from app.enums import Action

PERMITTED_ACTIONS: tuple[Action, ...] = (
    Action.DISCOVER,
    Action.RETRY_DISCOVERY,
    Action.CONTINUE_WITH_MINIMUM,
    Action.ASK_USER,
    Action.NEGOTIATE,
    Action.PLAN,
    Action.REVISE_PLAN,
    Action.PAYGUARD,
)

ACTION_DESCRIPTIONS: dict[Action, str] = {
    Action.DISCOVER: "Query the provider catalogue and rank verified candidates for each need.",
    Action.RETRY_DISCOVERY: "Relax non-mandatory preference filters and re-run provider discovery.",
    Action.CONTINUE_WITH_MINIMUM: "Proceed to provider offers using the minimum verified coverage (>= 1 per need).",
    Action.ASK_USER: "Pause the workflow with status NEEDS_INPUT and ask the user for clarification.",
    Action.NEGOTIATE: "Run a bounded negotiation round with candidate providers.",
    Action.PLAN: "Evaluate offer combinations within budget and select the optimal plan.",
    Action.REVISE_PLAN: "Request one extra negotiation round to bring offer combinations within budget.",
    Action.PAYGUARD: "Run PayGuard AI risk assessment and deterministic policy rules on the selected plan.",
}


def validate_action(raw_action: str | Action | None, allowed: Sequence[Action]) -> Action | None:
    """Return the matching `Action` if `raw_action` is in both `PERMITTED_ACTIONS` and `allowed`, else None."""
    if raw_action is None:
        return None
    value = raw_action.value if isinstance(raw_action, Action) else str(raw_action).strip()
    for candidate in allowed:
        if candidate in PERMITTED_ACTIONS and candidate.value == value:
            return candidate
    return None
