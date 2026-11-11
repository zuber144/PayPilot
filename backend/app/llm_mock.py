"""Deterministic offline responses for LLM_MODE=mock."""

from __future__ import annotations

import json
import re
from typing import Any


def _parse_user_payload(user: str) -> dict[str, Any]:
    try:
        parsed = json.loads(user)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return {"raw_text": user}


# Shopping-list keywords understood offline: (need key / category, keyword stems)
_PRODUCT_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("party_hats", ("hat",)),
    ("balloons", ("balloon",)),
]


def _item_quantity(text: str, stem: str) -> int | None:
    """Number directly before the item, allowing up to two adjectives: '10 party hats' -> 10."""
    match = re.search(rf"(\d+)\s+(?:[a-z-]+\s+){{0,2}}?{stem}", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _extract_deadline_days(text: str) -> int | None:
    match = re.search(r"(?:in|within)\s+(\d+)\s*days?", text, re.IGNORECASE)
    if not match:
        match = re.search(r"(\d+)\s*days?", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def respond(task: str, system: str, user: str) -> dict[str, Any]:
    """Return a deterministic dict matching the Pydantic schema for `task`."""
    _ = system
    payload = _parse_user_payload(user)

    if task == "goal_parse":
        raw_text = str(payload.get("raw_text") or payload.get("text") or payload.get("goal") or user)
        currency = str(payload.get("currency") or "USD")
        lowered = raw_text.lower()
        deadline_days = _extract_deadline_days(raw_text)

        needs: list[dict[str, Any]] = []
        for key, stems in _PRODUCT_KEYWORDS:
            stem = next((s for s in stems if s in lowered), None)
            if stem is None:
                continue
            needs.append(
                {
                    "key": key,
                    "category": key,
                    "quantity": _item_quantity(raw_text, stem),
                    "must_haves": [],
                }
            )

        if not needs:
            return {
                "needs": [],
                "deadline_days": deadline_days,
                "currency": currency,
                "question": (
                    "Could you list the products you want to buy and how many (e.g. 10 party hats)?"
                ),
            }
        return {
            "needs": needs,
            "deadline_days": deadline_days,
            "currency": currency,
            "question": None,
        }

    if task == "route":
        allowed = payload.get("allowed") or payload.get("allowed_actions") or []
        action = str(allowed[0]) if isinstance(allowed, list) and allowed else "ask_user"
        return {
            "action": action,
            "reason": f"Selected permitted action '{action}' based on workflow state.",
        }

    if task == "offer_text":
        provider_name = str(payload.get("provider_name") or payload.get("name") or "Seller")
        title = str(payload.get("product_title") or payload.get("category") or "item")
        packs = payload.get("packs") or 1
        days = payload.get("turnaround_days") or payload.get("timeline_days") or 5
        return {
            "scope": f"{packs} x {title} from {provider_name}, delivered in {days} days.",
            "pitch": "",
        }

    if task == "negotiation_text":
        round_no = payload.get("round") or payload.get("round_no") or 1
        return {
            "message": f"Comparison pass {round_no}: prices re-derived from listings.",
        }

    if task == "plan_rationale":
        return {
            "rationale": (
                "Selected the lowest-total cart of store listings within budget (shipping included), "
                "then preferring higher seller ratings and faster delivery."
            ),
        }

    if task == "risk":
        return {
            "risk_score": 0.1,
            "flags": [],
        }

    raise ValueError(f"Unsupported LLM task: {task}")
