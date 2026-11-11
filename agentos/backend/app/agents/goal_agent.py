"""Goal Agent: parses a free-text shopping request into a structured shopping list (needs).

Pure function: no DB writes, no trace writes.
"""

import json
from dataclasses import dataclass

from app.llm import LLMFailure, call_json
from app.schemas import GoalLLMOut, Need, ParsedGoal

_SYSTEM_PROMPT = (
    "You are the Goal Parsing Agent for PayPal AgentOS, a shopping assistant that compares store "
    "listings. Extract each distinct product to buy (unique snake_case key, category = short "
    "snake_case product search term such as 'party_hats' or 'balloons', integer quantity = number "
    "of units wanted, and must_haves list of attributes like colour or material), optional "
    "deadline_days (days until the items are needed), and 3-letter currency code. "
    "If the request names no concrete product, return an empty needs list and set a concise "
    "clarification question."
)

_DEFAULT_CLARIFICATION = (
    "Could you list the products you want to buy and how many of each "
    "(for example, 10 party hats and 50 balloons)?"
)


@dataclass
class GoalAgentResult:
    parsed: ParsedGoal | None
    question: str | None
    fallback: bool
    reason: str


def _normalize_needs(raw_needs: list[Need]) -> list[Need]:
    """Ensure needs have non-empty keys/categories and unique keys (preserving order)."""
    seen_keys: set[str] = set()
    unique_needs: list[Need] = []
    for item in raw_needs:
        key = item.key.strip().lower()
        category = item.category.strip().lower()
        if not key or not category:
            continue
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_needs.append(
            Need(
                key=key,
                category=category,
                quantity=item.quantity,
                must_haves=list(item.must_haves),
            )
        )
    return unique_needs


def run(raw_text: str, currency: str) -> GoalAgentResult:
    """Parse raw goal text into a validated ParsedGoal or a clarification question."""
    default_currency = (currency or "USD").strip().upper()
    if not raw_text or not raw_text.strip():
        return GoalAgentResult(
            parsed=None,
            question=_DEFAULT_CLARIFICATION,
            fallback=False,
            reason="Empty goal text",
        )

    user_payload = json.dumps({"raw_text": raw_text, "currency": default_currency})
    try:
        llm_out = call_json(_SYSTEM_PROMPT, user_payload, GoalLLMOut, task="goal_parse")
    except LLMFailure as exc:
        return GoalAgentResult(
            parsed=None,
            question=_DEFAULT_CLARIFICATION,
            fallback=True,
            reason=f"LLM goal parse failed: {exc}",
        )

    needs = _normalize_needs(llm_out.needs)
    if not needs:
        question = (llm_out.question or "").strip() or _DEFAULT_CLARIFICATION
        return GoalAgentResult(
            parsed=None,
            question=question,
            fallback=False,
            reason="No actionable needs identified in goal",
        )

    resolved_currency = (llm_out.currency or "").strip().upper() or default_currency
    parsed = ParsedGoal(
        needs=needs,
        deadline_days=llm_out.deadline_days,
        currency=resolved_currency,
    )
    return GoalAgentResult(
        parsed=parsed,
        question=None,
        fallback=False,
        reason=f"Parsed {len(needs)} need(s)",
    )
