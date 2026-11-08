"""
app/agents/goal_analyzer.py — Step 1 of the pipeline.

Parses raw user text + budget into a structured ParsedGoal.
The LLM writes the structured JSON; on failure the stub fallback is used.
"""
from __future__ import annotations

import re
from typing import List

from app.llm import complete_json
from app.schemas import ParsedGoal

# ---------------------------------------------------------------------------
# Keyword → need mappings used by the stub / fallback
# ---------------------------------------------------------------------------

_KEYWORD_NEEDS: dict[str, List[str]] = {
    "web": ["web_design", "copywriting"],
    "logo": ["logo_design", "brand_identity"],
    "app": ["app_development", "ui_ux_design"],
    "market": ["marketing", "social_media"],
    "video": ["video_production", "scriptwriting"],
    "photo": ["photography", "photo_editing"],
    "content": ["copywriting", "content_strategy"],
    "seo": ["seo", "copywriting"],
}


def _infer_needs(text: str) -> List[str]:
    """Deterministic fallback: map keywords in text to service needs."""
    lower = text.lower()
    found: List[str] = []
    for kw, needs in _KEYWORD_NEEDS.items():
        if kw in lower:
            for n in needs:
                if n not in found:
                    found.append(n)
    return found or ["general_service"]


def _infer_deadline(text: str) -> int:
    """Extract a deadline in days from text, or default to 30."""
    match = re.search(r"(\d+)\s*(day|week|month)", text.lower())
    if not match:
        return 30
    n, unit = int(match.group(1)), match.group(2)
    if unit.startswith("week"):
        return n * 7
    if unit.startswith("month"):
        return n * 30
    return n


def analyze_goal(
    raw_text: str,
    budget_minor: int,
    currency: str = "USD",
) -> tuple[ParsedGoal, bool]:
    """
    Parse a free-text goal description into a structured ParsedGoal.

    Returns (ParsedGoal, used_fallback).
    """
    # TODO(llm-owner): replace the stub prompt below with a real structured
    # extraction prompt that asks the LLM for needs[], deadline_days, etc.
    prompt = (
        f"goal_analyzer\n"
        f"Parse this goal into JSON with keys: needs (list of service need strings), "
        f"budget_minor (int cents), currency (3-letter ISO), deadline_days (int).\n\n"
        f"Goal: {raw_text}\n"
        f"Budget: {budget_minor} {currency}\n"
        f"Output JSON only."
    )

    fallback = ParsedGoal(
        needs=_infer_needs(raw_text),
        budget_minor=budget_minor,
        currency=currency,
        deadline_days=_infer_deadline(raw_text),
    )

    return complete_json(prompt, ParsedGoal, fallback)
