"""Bounded orchestrator router (`allowed_actions`, `default_action`, `choose_action`).

Computes the permitted actions from workflow state using deterministic rules, asks the LLM
to pick one, validates that the choice is in `allowed`, and falls back to the default action
with `fallback_used=True` on `LLMFailure` or disallowed selection.
"""

from __future__ import annotations

import json
from typing import Any

from app import llm
from app.config import settings
from app.enums import Action, TraceNode
from app.llm import LLMFailure
from app.orchestration.state import AgentState
from app.orchestration.tools import validate_action
from app.schemas import CoverageReport, RouteLLMOut

ROUTER_SYSTEM_PROMPT = (
    "You are the bounded AgentOS orchestrator. Choose the best next action strictly from the "
    "provided `allowed` list based on the workflow state summary, and return JSON matching "
    '{"action": "<allowed_action>", "reason": "<short reason>"}.'
)


def _infer_coverage(state: AgentState) -> tuple[bool, bool, dict[str, int]] | None:
    """Return `(sufficient, minimum_met, counts)` if discovery has occurred, else None."""
    cov = state.get("coverage")
    if isinstance(cov, CoverageReport):
        return cov.sufficient, cov.minimum_met, dict(cov.counts)
    if isinstance(cov, dict) and ("sufficient" in cov or "counts" in cov):
        counts = {str(k): int(v) for k, v in (cov.get("counts") or {}).items()}
        sufficient = bool(
            cov.get(
                "sufficient",
                bool(counts) and all(c >= settings.REQUIRED_COVERAGE for c in counts.values()),
            )
        )
        minimum_met = bool(
            cov.get(
                "minimum_met",
                bool(counts) and all(c >= settings.MIN_COVERAGE for c in counts.values()),
            )
        )
        return sufficient, minimum_met, counts

    candidates = state.get("candidates")
    stage = state.get("stage", "")
    if isinstance(candidates, dict) and (candidates or stage == "discovered"):
        needs = state.get("needs") or []
        need_keys = [str(n["key"]) if isinstance(n, dict) else n.key for n in needs]
        if not need_keys:
            need_keys = list(candidates.keys())
        counts = {}
        for key in need_keys:
            provs = candidates.get(key) or []
            verified_count = sum(
                1
                for p in provs
                if (
                    p.verified
                    if hasattr(p, "verified")
                    else bool(p.get("verified", True) if isinstance(p, dict) else True)
                )
            )
            counts[key] = verified_count
        sufficient = bool(counts) and all(c >= settings.REQUIRED_COVERAGE for c in counts.values())
        minimum_met = bool(counts) and all(c >= settings.MIN_COVERAGE for c in counts.values())
        return sufficient, minimum_met, counts

    return None


def _is_planning_failed(state: AgentState) -> bool:
    if state.get("plan") is not None:
        return False
    if state.get("stage") in ("planned", "no_plan", "planning_failed"):
        return True
    if state.get("planning_attempted") is True:
        return True
    trace = state.get("trace") or []
    if trace:
        last = trace[-1]
        node_val = last.node.value if hasattr(last, "node") and hasattr(last.node, "value") else (
            last.get("node") if isinstance(last, dict) else getattr(last, "node", None)
        )
        if node_val == TraceNode.PLANNING.value:
            return True
    return False


def allowed_actions(state: AgentState) -> list[Action]:
    """Compute the permitted orchestrator actions for `state` (work-division doc 3.3).

    The first element in the returned list is always the deterministic default action.
    """
    retries = state.get("retries") or {}
    discovery_retries = int(retries.get("discovery", 0))
    negotiation_rounds = int(retries.get("negotiation", 0))
    plan_revisions = int(retries.get("plan_revision", 0))

    # 1. Plan ready -> payguard
    if state.get("plan") is not None:
        return [Action.PAYGUARD]

    # 2. No plan within budget (after planning ran and found no valid combination)
    if _is_planning_failed(state):
        if plan_revisions < settings.MAX_PLAN_REVISIONS:
            return [Action.REVISE_PLAN, Action.ASK_USER]
        return [Action.ASK_USER]

    # 3. Offers ready -> negotiate (if rounds < MAX_NEGOTIATION_ROUNDS), plan.
    #    At least one negotiation round is mandatory: with no round run yet, negotiate is the
    #    only allowed action, so the LLM cannot skip straight to planning at list price.
    if state.get("offers"):
        if negotiation_rounds < settings.MAX_NEGOTIATION_ROUNDS:
            if negotiation_rounds == 0:
                return [Action.NEGOTIATE]
            return [Action.NEGOTIATE, Action.PLAN]
        return [Action.PLAN]

    # 4. After discovery -> coverage below required
    cov_info = _infer_coverage(state)
    if cov_info is not None:
        sufficient, minimum_met, _ = cov_info
        if not sufficient:
            allowed: list[Action] = []
            if discovery_retries < settings.MAX_DISCOVERY_RETRIES:
                allowed.append(Action.RETRY_DISCOVERY)
            if minimum_met:
                allowed.append(Action.CONTINUE_WITH_MINIMUM)
            allowed.append(Action.ASK_USER)
            return allowed
        return [Action.CONTINUE_WITH_MINIMUM]

    # 5. After goal parsed -> discover, ask_user (or ask_user only if needs empty / question set)
    needs = state.get("needs") or []
    if not needs or state.get("question"):
        return [Action.ASK_USER]
    return [Action.DISCOVER, Action.ASK_USER]


def default_action(state: AgentState) -> Action:
    """Return the deterministic default action for `state`."""
    allowed = allowed_actions(state)
    return allowed[0] if allowed else Action.ASK_USER


def choose_action(state: AgentState) -> tuple[Action, bool, str]:
    """Ask the LLM to choose from `allowed_actions(state)` and validate the result.

    Returns `(action, fallback_used, reason)`.
    """
    allowed = allowed_actions(state)
    if not allowed:
        return Action.ASK_USER, True, "No allowed actions; defaulting to ask_user."

    default = allowed[0]
    cov_info = _infer_coverage(state)
    summary: dict[str, Any] = {
        "allowed": [a.value for a in allowed],
        "stage": state.get("stage", "init"),
        "needs": [n.key if hasattr(n, "key") else str(n) for n in (state.get("needs") or [])],
        "coverage": cov_info[2] if cov_info else None,
        "coverage_sufficient": cov_info[0] if cov_info else None,
        "coverage_minimum_met": cov_info[1] if cov_info else None,
        "offers_count": len(state.get("offers") or []),
        "plan_ready": state.get("plan") is not None,
        "retries": dict(state.get("retries") or {}),
    }

    try:
        llm_out = llm.call_json(
            ROUTER_SYSTEM_PROMPT,
            json.dumps(summary),
            RouteLLMOut,
            task="route",
        )
    except LLMFailure as exc:
        return default, True, f"Router LLM failed ({exc}); fell back to default action '{default.value}'."

    chosen = validate_action(llm_out.action, allowed)
    if chosen is None:
        return (
            default,
            True,
            f"Router LLM returned disallowed action '{llm_out.action}'; fell back to default '{default.value}'.",
        )

    default_reason = f"Selected '{chosen.value}' from {[a.value for a in allowed]}."
    reason = llm_out.reason.strip() if llm_out.reason else default_reason
    return chosen, False, reason
