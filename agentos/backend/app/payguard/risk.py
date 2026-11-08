"""
app/payguard/risk.py — AI risk layer (STUB).

Returns a risk assessment with a score and flag codes.
Flag codes are a CLOSED set — do not add new codes without updating the enum.

TODO(ai-owner): Replace this stub with a real LLM call that:
  1. Receives the plan items, provider details, and goal context.
  2. Returns a risk_score (0-100) and relevant flags from the closed set below.
  3. Writes a human-readable summary explaining the risk factors.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class RiskFlag(str, Enum):
    PRICE_ANOMALY = "PRICE_ANOMALY"
    SCOPE_VAGUE = "SCOPE_VAGUE"
    GOAL_MISMATCH = "GOAL_MISMATCH"
    VENDOR_CONCENTRATION = "VENDOR_CONCENTRATION"
    UNUSUAL_TIMELINE = "UNUSUAL_TIMELINE"


class RiskResult(BaseModel):
    risk_score: Optional[int]  # 0-100; None means LLM unavailable
    flags: list[RiskFlag]
    summary: str


def assess_risk(
    plan_items: list[dict],
    goal_text: str,
    budget_minor: int,
) -> RiskResult:
    """
    Stub risk assessment. Returns deterministic results based on simple heuristics.

    TODO(ai-owner): Replace with a real LLM call. The stub uses simple
    heuristics so the three demo goals produce APPROVED / REVIEW / BLOCKED
    outcomes for demonstration purposes.
    """
    flags: list[RiskFlag] = []
    risk_score = 20  # baseline — low risk

    # Heuristic 1: single vendor covers >70% of budget → concentration risk
    if len(plan_items) == 1 and plan_items[0].get("price_minor", 0) > 0.7 * budget_minor:
        flags.append(RiskFlag.VENDOR_CONCENTRATION)
        risk_score += 30

    # Heuristic 2: vague goal text
    vague_words = {"help", "stuff", "things", "something", "etc"}
    if any(w in goal_text.lower().split() for w in vague_words):
        flags.append(RiskFlag.SCOPE_VAGUE)
        risk_score += 15

    # Heuristic 3: unusually cheap (< 20% of budget used)
    total = sum(item.get("price_minor", 0) for item in plan_items)
    if total < 0.20 * budget_minor and budget_minor > 10000:
        flags.append(RiskFlag.PRICE_ANOMALY)
        risk_score += 10

    risk_score = min(risk_score, 100)

    summary_parts = []
    if not flags:
        summary_parts.append("No significant risk factors detected.")
    else:
        summary_parts.append(f"Risk factors identified: {', '.join(f.value for f in flags)}.")

    return RiskResult(
        risk_score=risk_score,
        flags=flags,
        summary=" ".join(summary_parts),
    )
