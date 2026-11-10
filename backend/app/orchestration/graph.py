"""LangGraph workflow (`build_graph`, `run_workflow`) for AgentOS + PayGuard."""

from __future__ import annotations

import sys
import time
from types import SimpleNamespace
from typing import Any

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app import db as db_module
from app.config import settings
from app.enums import (
    Action,
    GoalStatus,
    OfferStatus,
    PlanStatus,
    Scenario,
    TraceNode,
    TraceStatus,
)
from app.models import Goal, Offer, Plan, Provider
from app.orchestration import router
from app.orchestration.state import AgentState, append_trace, get_filters, make_initial_state
from app.schemas import (
    CoverageReport,
    Filters,
    Need,
    OfferDraft,
    PayGuardResult,
    PlanDraft,
    ProviderOut,
)

# Module-level placeholders so unit tests can import and monkeypatch `graph.<agent>` even before
# sibling packages are imported, while resolving live modules from `app.agents` / `app.payguard`.
try:
    from app.agents import (  # type: ignore[attr-defined]
        discovery_agent,
        goal_agent,
        negotiation_agent,
        planning_agent,
        provider_agent,
    )
except Exception:  # pragma: no cover - fallback stub if imported before agents exist
    goal_agent = SimpleNamespace(run=None)  # type: ignore[assignment]
    discovery_agent = SimpleNamespace(initial_filters=None, relax_filters=None, run=None)  # type: ignore[assignment]
    provider_agent = SimpleNamespace(run=None)  # type: ignore[assignment]
    negotiation_agent = SimpleNamespace(run_round=None)  # type: ignore[assignment]
    planning_agent = SimpleNamespace(run=None)  # type: ignore[assignment]

try:
    from app.payguard import engine as payguard_engine  # type: ignore[attr-defined]
except Exception:  # pragma: no cover - fallback stub if imported before payguard exists
    payguard_engine = SimpleNamespace(run_payguard=None)  # type: ignore[assignment]


def _resolve_agent(module_attr: Any, dotted_path: str) -> Any:
    """Return `module_attr` if its functions are populated, otherwise import `dotted_path`."""
    if module_attr is not None and any(
        callable(getattr(module_attr, fn, None))
        for fn in ("run", "run_round", "run_payguard", "initial_filters")
    ):
        return module_attr
    if dotted_path in sys.modules:
        return sys.modules[dotted_path]
    __import__(dotted_path)
    return sys.modules[dotted_path]


def _elapsed_ms(start_ns: int) -> int:
    return max(0, int((time.perf_counter_ns() - start_ns) / 1_000_000))


def _persist_goal_progress(db: Session | None, state: AgentState) -> None:
    if db is None:
        return
    goal = db.get(Goal, state["goal_id"])
    if goal is None:
        return
    goal.trace = [e.model_dump(mode="json") for e in state.get("trace", [])]
    if state.get("status"):
        goal.status = state["status"]
    if state.get("question") is not None:
        goal.question = state["question"]
    if state.get("currency"):
        goal.currency = state["currency"]
    db.commit()


def _check_step_limit(db: Session | None, state: AgentState, node: TraceNode) -> bool:
    """Increment step counter and return True if `MAX_GRAPH_STEPS` is exceeded."""
    steps = int(state.get("steps", 0)) + 1
    state["steps"] = steps
    if steps > settings.MAX_GRAPH_STEPS:
        append_trace(
            state,
            node=node,
            action="max_steps_exceeded",
            status=TraceStatus.ERROR,
            summary=f"Workflow terminated: exceeded MAX_GRAPH_STEPS ({settings.MAX_GRAPH_STEPS})",
            reason=f"Step count {steps} > MAX_GRAPH_STEPS ({settings.MAX_GRAPH_STEPS}).",
            duration_ms=0,
            data={"steps": steps, "max_graph_steps": settings.MAX_GRAPH_STEPS},
        )
        state["status"] = GoalStatus.FAILED.value
        state["next_action"] = "end"
        _persist_goal_progress(db, state)
        return True
    return False


def make_nodes(db: Session | None = None) -> dict[str, Any]:
    """Build node callables bound to optional SQLAlchemy session `db`."""

    def goal_node(state: AgentState) -> AgentState:
        if _check_step_limit(db, state, TraceNode.GOAL):
            return state
        t0 = time.perf_counter_ns()
        ga = _resolve_agent(goal_agent, "app.agents.goal_agent")
        res = ga.run(state["raw_text"], state["currency"])

        parsed = getattr(res, "parsed", None) if not isinstance(res, dict) else res.get("parsed")
        question = getattr(res, "question", None) if not isinstance(res, dict) else res.get("question")
        fallback = bool(getattr(res, "fallback", False) if not isinstance(res, dict) else res.get("fallback", False))
        reason = str(getattr(res, "reason", "") if not isinstance(res, dict) else res.get("reason", ""))

        da = _resolve_agent(discovery_agent, "app.agents.discovery_agent")
        init_filters_fn = getattr(da, "initial_filters", None)
        if callable(init_filters_fn):
            f_obj = init_filters_fn(state.get("scenario"))
            state["filters"] = f_obj.model_dump() if isinstance(f_obj, Filters) else dict(f_obj)
        elif state.get("scenario") == Scenario.RETRY.value:
            state["filters"] = Filters(min_rating=4.5, max_turnaround_days=5).model_dump()

        if state.get("scenario") == Scenario.BLOCKED.value:
            state["include_unverified"] = True

        duration = _elapsed_ms(t0)
        needs_list: list[Need] = list(parsed.needs) if parsed and getattr(parsed, "needs", None) else []

        if parsed is None or not needs_list:
            q = question or "Please clarify which services and quantities you need."
            state["needs"] = []
            state["question"] = q
            state["stage"] = "goal_parsed"
            append_trace(
                state,
                node=TraceNode.GOAL,
                action="parse_goal",
                status=TraceStatus.FALLBACK if fallback else TraceStatus.OK,
                summary="Goal needs clarification from user",
                reason=reason or q,
                duration_ms=duration,
                data={"question": q},
            )
            if db is not None:
                goal = db.get(Goal, state["goal_id"])
                if goal is not None:
                    goal.parsed = parsed.model_dump(mode="json") if parsed else None
                    goal.question = q
            _persist_goal_progress(db, state)
            return state

        state["needs"] = needs_list
        state["deadline_days"] = parsed.deadline_days
        if getattr(parsed, "currency", None):
            state["currency"] = parsed.currency
        state["question"] = None
        state["stage"] = "goal_parsed"

        append_trace(
            state,
            node=TraceNode.GOAL,
            action="parse_goal",
            status=TraceStatus.FALLBACK if fallback else TraceStatus.OK,
            summary=f"Extracted {len(needs_list)} need(s): {', '.join(n.key for n in needs_list)}",
            reason=reason or "Parsed structured needs from goal description.",
            duration_ms=duration,
            data={
                "needs": [n.model_dump(mode="json") for n in needs_list],
                "deadline_days": parsed.deadline_days,
                "currency": state["currency"],
            },
        )
        if db is not None:
            goal = db.get(Goal, state["goal_id"])
            if goal is not None:
                goal.parsed = parsed.model_dump(mode="json")
                goal.currency = state["currency"]
        _persist_goal_progress(db, state)
        return state

    def discovery_node(state: AgentState) -> AgentState:
        if _check_step_limit(db, state, TraceNode.DISCOVERY):
            return state
        t0 = time.perf_counter_ns()
        da = _resolve_agent(discovery_agent, "app.agents.discovery_agent")

        providers_by_id = dict(state.get("providers_by_id") or {})
        if not providers_by_id and db is not None:
            rows = db.query(Provider).order_by(Provider.id).all()
            providers_by_id = {r.id: ProviderOut.model_validate(r) for r in rows}
            state["providers_by_id"] = providers_by_id

        provider_list = list(providers_by_id.values())
        filters = get_filters(state)
        include_unverified = bool(state.get("include_unverified", False))

        candidates, coverage = da.run(
            provider_list,
            state.get("needs", []),
            filters,
            include_unverified=include_unverified,
        )
        state["candidates"] = candidates
        state["coverage"] = coverage
        state["stage"] = "discovered"

        duration = _elapsed_ms(t0)
        append_trace(
            state,
            node=TraceNode.DISCOVERY,
            action="discover_providers",
            status=TraceStatus.OK,
            summary=(
                f"Verified coverage {coverage.counts} "
                f"({'sufficient' if coverage.sufficient else 'insufficient'}, required {coverage.required})"
            ),
            reason="Filtered and ranked providers by verification, rating, turnaround and price.",
            duration_ms=duration,
            data={
                "counts": coverage.counts,
                "required": coverage.required,
                "sufficient": coverage.sufficient,
                "minimum_met": coverage.minimum_met,
                "filters": filters.model_dump(),
            },
        )
        _persist_goal_progress(db, state)
        return state

    def provider_node(state: AgentState) -> AgentState:
        if _check_step_limit(db, state, TraceNode.PROVIDER):
            return state
        t0 = time.perf_counter_ns()
        pa = _resolve_agent(provider_agent, "app.agents.provider_agent")

        opening_offers: list[OfferDraft] = []
        any_fallback = False
        candidates = state.get("candidates") or {}

        for need in state.get("needs", []):
            need_cands = candidates.get(need.key, [])
            offers_for_need, fb = pa.run(need, need_cands)
            opening_offers.extend(offers_for_need)
            any_fallback = any_fallback or bool(fb)

        state["offers"] = list(opening_offers)
        state["all_offers"] = list(opening_offers)
        state["stage"] = "offers_ready"

        if db is not None:
            for off in opening_offers:
                db.add(
                    Offer(
                        goal_id=state["goal_id"],
                        provider_id=off.provider_id,
                        need_key=off.need_key,
                        round=off.round,
                        price_minor=off.price_minor,
                        counter_minor=off.counter_minor,
                        scope=off.scope,
                        timeline_days=off.timeline_days,
                        status=off.status.value if isinstance(off.status, OfferStatus) else str(off.status),
                    )
                )

        duration = _elapsed_ms(t0)
        append_trace(
            state,
            node=TraceNode.PROVIDER,
            action="create_offers",
            status=TraceStatus.FALLBACK if any_fallback else TraceStatus.OK,
            summary=f"Created {len(opening_offers)} opening offer(s)",
            reason=(
                "Used deterministic fallback scope text for one or more offers."
                if any_fallback
                else "Generated opening offers using provider base prices."
            ),
            duration_ms=duration,
            data={"offers_count": len(opening_offers), "fallback": any_fallback},
        )
        _persist_goal_progress(db, state)
        return state

    def negotiation_node(state: AgentState) -> AgentState:
        if _check_step_limit(db, state, TraceNode.NEGOTIATION):
            return state
        t0 = time.perf_counter_ns()
        na = _resolve_agent(negotiation_agent, "app.agents.negotiation_agent")

        retries = dict(state.get("retries") or {})
        round_no = int(retries.get("negotiation", 0)) + 1
        retries["negotiation"] = round_no
        state["retries"] = retries

        effective_round = max(1, min(round_no, settings.MAX_NEGOTIATION_ROUNDS))
        raw_offers: list[OfferDraft] = na.run_round(
            state.get("offers", []),
            state.get("providers_by_id", {}),
            effective_round,
        )
        updated_offers: list[OfferDraft] = [
            o.model_copy(update={"round": round_no}) if o.round != round_no else o
            for o in raw_offers
        ]
        state["offers"] = list(updated_offers)
        all_offers = list(state.get("all_offers") or [])
        all_offers.extend(updated_offers)
        state["all_offers"] = all_offers
        state["stage"] = "offers_ready"
        state["planning_attempted"] = False

        if db is not None:
            for off in updated_offers:
                db.add(
                    Offer(
                        goal_id=state["goal_id"],
                        provider_id=off.provider_id,
                        need_key=off.need_key,
                        round=off.round,
                        price_minor=off.price_minor,
                        counter_minor=off.counter_minor,
                        scope=off.scope,
                        timeline_days=off.timeline_days,
                        status=off.status.value if isinstance(off.status, OfferStatus) else str(off.status),
                    )
                )

        duration = _elapsed_ms(t0)
        append_trace(
            state,
            node=TraceNode.NEGOTIATION,
            action=f"negotiate_round_{round_no}",
            status=TraceStatus.OK,
            summary=f"Completed negotiation round {round_no} across {len(updated_offers)} offer(s)",
            reason="Applied bounded counter-offer and provider concession rules.",
            duration_ms=duration,
            data={
                "round": round_no,
                "prices": {f"{o.need_key}:{o.provider_id}": o.price_minor for o in updated_offers},
            },
        )
        _persist_goal_progress(db, state)
        return state

    def planning_node(state: AgentState) -> AgentState:
        if _check_step_limit(db, state, TraceNode.PLANNING):
            return state
        t0 = time.perf_counter_ns()
        pla = _resolve_agent(planning_agent, "app.agents.planning_agent")

        plan_draft, fb = pla.run(
            state.get("offers", []),
            state.get("needs", []),
            state.get("providers_by_id", {}),
            state["budget_minor"],
            state["currency"],
        )
        state["plan"] = plan_draft
        state["stage"] = "planned"
        state["planning_attempted"] = True

        duration = _elapsed_ms(t0)
        if plan_draft is not None:
            summary_msg = (
                f"Selected plan totalling {plan_draft.total_minor} minor units "
                f"({len(plan_draft.items)} item(s))"
            )
            append_trace(
                state,
                node=TraceNode.PLANNING,
                action="select_plan",
                status=TraceStatus.FALLBACK if fb else TraceStatus.OK,
                summary=summary_msg,
                reason=(
                    "Used fallback template rationale due to LLM failure."
                    if fb
                    else "Picked lowest-cost valid provider combination within budget."
                ),
                duration_ms=duration,
                data={
                    "total_minor": plan_draft.total_minor,
                    "budget_minor": state["budget_minor"],
                    "items": [i.model_dump(mode="json") for i in plan_draft.items],
                    "fallback": bool(fb),
                },
            )
        else:
            append_trace(
                state,
                node=TraceNode.PLANNING,
                action="select_plan",
                status=TraceStatus.OK,
                summary="No valid offer combination within budget",
                reason=f"Every combination exceeded budget of {state['budget_minor']} minor units.",
                duration_ms=duration,
                data={"budget_minor": state["budget_minor"]},
            )
        _persist_goal_progress(db, state)
        return state

    def payguard_node(state: AgentState) -> AgentState:
        if _check_step_limit(db, state, TraceNode.PAYGUARD):
            return state
        t0 = time.perf_counter_ns()
        pge = _resolve_agent(payguard_engine, "app.payguard.engine")

        plan_draft: PlanDraft | None = state.get("plan")
        if plan_draft is None:
            state["status"] = GoalStatus.FAILED.value
            state["next_action"] = "end"
            append_trace(
                state,
                node=TraceNode.PAYGUARD,
                action="evaluate_plan",
                status=TraceStatus.ERROR,
                summary="PayGuard invoked without a selected plan",
                reason="Missing plan in state.",
                duration_ms=_elapsed_ms(t0),
            )
            _persist_goal_progress(db, state)
            return state

        other_plan_statuses: list[str] = []
        if db is not None:
            existing = db.query(Plan).filter(Plan.goal_id == state["goal_id"]).all()
            other_plan_statuses = [p.status for p in existing]

        pg_result: PayGuardResult = pge.run_payguard(
            plan_draft,
            state["budget_minor"],
            state["currency"],
            state["raw_text"],
            state.get("providers_by_id", {}),
            other_plan_statuses,
        )
        state["payguard"] = pg_result
        state["stage"] = "checked"
        state["status"] = GoalStatus.PLAN_READY.value

        chosen_pairs = {(item.need_key, item.provider_id) for item in plan_draft.items}
        for off in state.get("offers", []):
            if (off.need_key, off.provider_id) in chosen_pairs:
                off.status = OfferStatus.SELECTED

        if db is not None:
            plan_row = Plan(
                goal_id=state["goal_id"],
                items=[i.model_dump(mode="json") for i in plan_draft.items],
                total_minor=plan_draft.total_minor,
                currency=plan_draft.currency,
                rationale=plan_draft.rationale,
                payguard_result=pg_result.model_dump(mode="json"),
                acknowledged_flags=[],
                status=PlanStatus.CHECKED.value,
            )
            db.add(plan_row)
            db.flush()
            state["plan_id"] = plan_row.id

            for need_key, provider_id in chosen_pairs:
                latest_offer = (
                    db.query(Offer)
                    .filter(
                        Offer.goal_id == state["goal_id"],
                        Offer.need_key == need_key,
                        Offer.provider_id == provider_id,
                    )
                    .order_by(Offer.round.desc(), Offer.id.desc())
                    .first()
                )
                if latest_offer is not None:
                    latest_offer.status = OfferStatus.SELECTED.value

        duration = _elapsed_ms(t0)
        append_trace(
            state,
            node=TraceNode.PAYGUARD,
            action="evaluate_plan",
            status=TraceStatus.FALLBACK if not pg_result.ai_ok else TraceStatus.OK,
            summary=f"PayGuard verdict: {pg_result.verdict.value}",
            reason=(
                "AI risk check unavailable; verdict capped at REVIEW."
                if not pg_result.ai_ok
                else f"Completed policy and AI risk evaluation (risk_score={pg_result.risk_score})."
            ),
            duration_ms=duration,
            data={
                "verdict": pg_result.verdict.value,
                "risk_score": pg_result.risk_score,
                "ai_ok": pg_result.ai_ok,
                "flags": [f.model_dump(mode="json") for f in pg_result.flags],
            },
        )
        _persist_goal_progress(db, state)
        return state

    def orchestrator_node(state: AgentState) -> AgentState:
        if _check_step_limit(db, state, TraceNode.ORCHESTRATOR):
            return state
        t0 = time.perf_counter_ns()
        allowed = router.allowed_actions(state)
        action, fallback_used, reason = router.choose_action(state)
        state["next_action"] = action.value
        retries = dict(state.get("retries") or {})
        duration = _elapsed_ms(t0)

        if action == Action.RETRY_DISCOVERY:
            attempt = int(retries.get("discovery", 0)) + 1
            retries["discovery"] = attempt
            state["retries"] = retries

            da = _resolve_agent(discovery_agent, "app.agents.discovery_agent")
            current_filters = get_filters(state)
            relax_fn = getattr(da, "relax_filters", None)
            if callable(relax_fn):
                new_filters, relaxed = relax_fn(current_filters, attempt)
            else:
                relaxed = ["min_rating"] if attempt == 1 else ["max_turnaround_days"]
                new_filters = Filters(
                    min_rating=None if attempt >= 1 else current_filters.min_rating,
                    max_turnaround_days=None if attempt >= 2 else current_filters.max_turnaround_days,
                    price_ceiling_minor=current_filters.price_ceiling_minor,
                )
            state["filters"] = new_filters.model_dump() if isinstance(new_filters, Filters) else dict(new_filters)
            state["last_relaxed"] = list(relaxed)

            cov = state.get("coverage")
            counts = cov.counts if isinstance(cov, CoverageReport) else {}
            required = cov.required if isinstance(cov, CoverageReport) else settings.REQUIRED_COVERAGE
            deficient = [k for k, v in counts.items() if v < required]
            target_need = (
                "photography"
                if "photography" in deficient
                else (deficient[0] if deficient else (state["needs"][0].key if state.get("needs") else "need"))
            )
            retry_reason = (
                f"Coverage < {required} for need '{target_need}'; "
                f"retry {attempt} of {settings.MAX_DISCOVERY_RETRIES}"
            )
            retry_summary = (
                f"Insufficient verified coverage for '{target_need}'; "
                f"retrying discovery ({attempt}/{settings.MAX_DISCOVERY_RETRIES})"
            )
            append_trace(
                state,
                node=TraceNode.ORCHESTRATOR,
                action=Action.RETRY_DISCOVERY.value,
                status=TraceStatus.RETRY,
                summary=retry_summary,
                reason=retry_reason,
                duration_ms=duration,
                data={"relaxed": list(relaxed), "attempt": attempt, "allowed": [a.value for a in allowed]},
            )
            _persist_goal_progress(db, state)
            return state

        if action == Action.REVISE_PLAN:
            rev = int(retries.get("plan_revision", 0)) + 1
            retries["plan_revision"] = rev
            state["retries"] = retries
            state["stage"] = "offers_ready"
            state["planning_attempted"] = False
            append_trace(
                state,
                node=TraceNode.ORCHESTRATOR,
                action=Action.REVISE_PLAN.value,
                status=TraceStatus.FALLBACK if fallback_used else TraceStatus.RETRY,
                summary=f"Revising plan via extra negotiation round ({rev}/{settings.MAX_PLAN_REVISIONS})",
                reason=reason or f"No plan within budget; revision {rev} of {settings.MAX_PLAN_REVISIONS}",
                duration_ms=duration,
                data={"revision": rev, "allowed": [a.value for a in allowed], "fallback": fallback_used},
            )
            _persist_goal_progress(db, state)
            return state

        if action == Action.ASK_USER:
            q = state.get("question") or (
                "We could not find enough verified providers or a plan within your budget. "
                "Could you adjust your goal or budget?"
            )
            state["question"] = q
            state["status"] = GoalStatus.NEEDS_INPUT.value
            append_trace(
                state,
                node=TraceNode.ORCHESTRATOR,
                action=Action.ASK_USER.value,
                status=TraceStatus.FALLBACK if fallback_used else TraceStatus.OK,
                summary="Asking user for clarification",
                reason=reason,
                duration_ms=duration,
                data={"question": q, "allowed": [a.value for a in allowed], "fallback": fallback_used},
            )
            _persist_goal_progress(db, state)
            return state

        append_trace(
            state,
            node=TraceNode.ORCHESTRATOR,
            action=action.value,
            status=TraceStatus.FALLBACK if fallback_used else TraceStatus.OK,
            summary=f"Orchestrator chose '{action.value}'",
            reason=reason,
            duration_ms=duration,
            data={"allowed": [a.value for a in allowed], "fallback": fallback_used},
        )
        _persist_goal_progress(db, state)
        return state

    return {
        "goal": goal_node,
        "discovery": discovery_node,
        "provider": provider_node,
        "negotiation": negotiation_node,
        "planning": planning_node,
        "payguard": payguard_node,
        "orchestrator": orchestrator_node,
    }


def _route_after_node(state: AgentState) -> str:
    if state.get("status") == GoalStatus.FAILED.value or state.get("next_action") == "end":
        return "end"
    return "orchestrator"


def _route_after_discovery(state: AgentState) -> str:
    if state.get("status") == GoalStatus.FAILED.value or state.get("next_action") == "end":
        return "end"
    cov = state.get("coverage")
    if isinstance(cov, CoverageReport) and cov.sufficient:
        return "provider"
    if isinstance(cov, dict) and cov.get("sufficient"):
        return "provider"
    return "orchestrator"


def _route_from_orchestrator(state: AgentState) -> str:
    if state.get("status") in (GoalStatus.FAILED.value, GoalStatus.NEEDS_INPUT.value):
        return "end"
    nxt = state.get("next_action")
    if nxt in (Action.DISCOVER.value, Action.RETRY_DISCOVERY.value):
        return "discovery"
    if nxt == Action.CONTINUE_WITH_MINIMUM.value:
        return "provider"
    if nxt in (Action.NEGOTIATE.value, Action.REVISE_PLAN.value):
        return "negotiation"
    if nxt == Action.PLAN.value:
        return "planning"
    if nxt == Action.PAYGUARD.value:
        return "payguard"
    return "end"


def build_graph(db: Session | None = None) -> Any:
    """Compile and return the AgentOS LangGraph `StateGraph`."""
    nodes = make_nodes(db)
    workflow = StateGraph(AgentState)

    for name, fn in nodes.items():
        workflow.add_node(name, fn)

    workflow.add_edge(START, "goal")
    workflow.add_conditional_edges(
        "goal",
        _route_after_node,
        {"orchestrator": "orchestrator", "end": END},
    )
    workflow.add_conditional_edges(
        "discovery",
        _route_after_discovery,
        {"provider": "provider", "orchestrator": "orchestrator", "end": END},
    )
    workflow.add_conditional_edges(
        "provider",
        _route_after_node,
        {"orchestrator": "orchestrator", "end": END},
    )
    workflow.add_conditional_edges(
        "negotiation",
        _route_after_node,
        {"orchestrator": "orchestrator", "end": END},
    )
    workflow.add_conditional_edges(
        "planning",
        _route_after_node,
        {"orchestrator": "orchestrator", "end": END},
    )
    workflow.add_edge("payguard", END)
    workflow.add_conditional_edges(
        "orchestrator",
        _route_from_orchestrator,
        {
            "discovery": "discovery",
            "provider": "provider",
            "negotiation": "negotiation",
            "planning": "planning",
            "payguard": "payguard",
            "end": END,
        },
    )

    return workflow.compile()


def run_workflow(goal_id: int) -> None:
    """Execute the full AgentOS + PayGuard workflow for `goal_id`.

    Opens its own `SessionLocal` session and never raises: any unhandled error marks the goal
    `FAILED` and appends an `ERROR` trace event.
    """
    try:
        with db_module.SessionLocal() as db:
            goal = db.get(Goal, goal_id)
            if goal is None:
                return

            state = make_initial_state(
                goal_id=goal.id,
                raw_text=goal.raw_text,
                budget_minor=goal.budget_minor,
                currency=goal.currency,
                scenario=goal.scenario,
                include_unverified=(goal.scenario == Scenario.BLOCKED.value),
            )
            compiled = build_graph(db)
            compiled.invoke(
                state,
                config={"recursion_limit": settings.MAX_GRAPH_STEPS * 2 + 10},
            )
    except Exception as exc:  # noqa: BLE001
        try:
            with db_module.SessionLocal() as err_db:
                goal = err_db.get(Goal, goal_id)
                if goal is not None:
                    existing_raw = list(goal.trace or [])
                    trace_state: AgentState = {"trace": []}
                    for item in existing_raw:
                        if isinstance(item, dict):
                            from app.schemas import TraceEvent

                            trace_state["trace"].append(TraceEvent.model_validate(item))
                    append_trace(
                        trace_state,
                        node=TraceNode.ORCHESTRATOR,
                        action="workflow_error",
                        status=TraceStatus.ERROR,
                        summary="Workflow failed with an unexpected error",
                        reason=f"{type(exc).__name__}: {exc}",
                        duration_ms=0,
                    )
                    goal.status = GoalStatus.FAILED.value
                    goal.trace = [e.model_dump(mode="json") for e in trace_state["trace"]]
                    err_db.commit()
        except Exception:  # noqa: BLE001
            pass
