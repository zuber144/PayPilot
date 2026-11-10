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


def _extract_quantity(text: str) -> int | None:
    match = re.search(r"for\s+(\d+)\s*(?:people|persons|guests|pax)?", text, re.IGNORECASE)
    if not match:
        match = re.search(r"(\d+)\s*(?:people|persons|guests|pax)", text, re.IGNORECASE)
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
        currency = str(payload.get("currency") or "INR")
        lowered = raw_text.lower()
        quantity = _extract_quantity(raw_text)
        deadline_days = _extract_deadline_days(raw_text)

        needs: list[dict[str, Any]] = []
        if any(kw in lowered for kw in ("cater", "food", "meal", "lunch", "dinner", "buffet")):
            needs.append(
                {
                    "key": "catering",
                    "category": "catering",
                    "quantity": quantity,
                    "must_haves": [],
                }
            )
        if any(kw in lowered for kw in ("photo", "camera", "shoot", "videograph")):
            needs.append(
                {
                    "key": "photography",
                    "category": "photography",
                    "quantity": 1,
                    "must_haves": [],
                }
            )

        if not needs:
            return {
                "needs": [],
                "deadline_days": deadline_days,
                "currency": currency,
                "question": (
                    "Could you clarify which services you need (e.g. catering or photography) and the headcount?"
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
        provider_name = str(payload.get("provider_name") or payload.get("name") or "Provider")
        category = str(payload.get("category") or payload.get("need_key") or "service")
        days = payload.get("turnaround_days") or payload.get("timeline_days") or 7
        return {
            "scope": f"Complete {category} package from {provider_name}, delivered within {days} days.",
            "pitch": f"Reliable {category} service tailored to your event requirements.",
        }

    if task == "negotiation_text":
        round_no = payload.get("round") or payload.get("round_no") or 1
        return {
            "message": f"Round {round_no} counter-offer evaluated within provider pricing bounds.",
        }

    if task == "plan_rationale":
        return {
            "rationale": (
                "Selected the lowest-total combination of verified providers within budget, "
                "prioritising provider rating and turnaround time."
            ),
        }

    if task == "risk":
        return {
            "risk_score": 0.1,
            "flags": [],
        }

    raise ValueError(f"Unsupported LLM task: {task}")
