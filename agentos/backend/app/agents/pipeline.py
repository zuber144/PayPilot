"""
app/agents/pipeline.py — PipelineRunner orchestrates the 5 agent steps.

Each step records a trace event:
  {step, summary, duration_ms, status: "ok"|"error"|"fallback", used_fallback}

The pipeline updates goals.trace and goals.status as it runs.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.agents.discovery import discover_providers
from app.agents.goal_analyzer import analyze_goal
from app.agents.negotiation import negotiate_all
from app.agents.plan_generator import generate_plan
from app.agents.provider_agent import ProviderAgent
from app.models import Goal, Offer, Plan
from app.schemas import NegotiatedOffer, ProviderOut

logger = logging.getLogger(__name__)


def _trace_event(
    step: str,
    summary: str,
    duration_ms: int,
    status: str,
    used_fallback: bool = False,
) -> dict[str, Any]:
    return {
        "step": step,
        "summary": summary,
        "duration_ms": duration_ms,
        "status": status,
        "used_fallback": used_fallback,
    }


def _update_goal(db: Session, goal: Goal, **kwargs: Any) -> None:
    for k, v in kwargs.items():
        setattr(goal, k, v)
    db.commit()
    db.refresh(goal)


class PipelineRunner:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run(self, goal_id: int) -> None:
        """Run the full pipeline for the given goal. Commits results to DB."""
        db = self.db
        goal = db.get(Goal, goal_id)
        if not goal:
            logger.error("Goal %d not found", goal_id)
            return

        trace: list[dict[str, Any]] = list(goal.trace or [])
        goal.status = "RUNNING"
        goal.trace = trace
        # Clean up any existing offers/plans for this goal
        db.query(Offer).filter(Offer.goal_id == goal_id).delete()
        existing_plan = db.query(Plan).filter(Plan.goal_id == goal_id).first()
        if existing_plan:
            db.delete(existing_plan)
        db.commit()

        try:
            self._run_pipeline(goal, trace)
        except Exception as exc:
            db.rollback()
            logger.exception("Pipeline failed for goal %d: %s", goal_id, exc)
            trace.append(
                _trace_event("pipeline", f"Fatal error: {exc}", 0, "error")
            )
            goal.status = "FAILED"
            goal.trace = list(trace)
            db.commit()

    def _run_pipeline(self, goal: Goal, trace: list[dict[str, Any]]) -> None:
        db = self.db

        # ── Step 1: Goal Analyzer ───────────────────────────────────────────
        t0 = time.monotonic()
        parsed, used_fallback = analyze_goal(goal.raw_text, goal.budget_minor, goal.currency)
        ms = int((time.monotonic() - t0) * 1000)

        trace.append(
            _trace_event(
                "goal_analyzer",
                f"Identified {len(parsed.needs)} needs: {', '.join(parsed.needs)}",
                ms,
                "fallback" if used_fallback else "ok",
                used_fallback,
            )
        )
        goal.parsed = parsed.model_dump()
        goal.trace = list(trace)
        db.commit()

        # ── Step 2: Service Discovery ───────────────────────────────────────
        t0 = time.monotonic()
        discovery_results = discover_providers(
            db, parsed.needs, goal.budget_minor, goal.currency
        )
        ms = int((time.monotonic() - t0) * 1000)

        provider_count = sum(len(r.providers) for r in discovery_results)
        trace.append(
            _trace_event(
                "discovery",
                f"Found {provider_count} provider(s) across {len(discovery_results)} need(s)",
                ms,
                "ok",
            )
        )
        goal.trace = list(trace)
        db.commit()

        if not any(r.providers for r in discovery_results):
            trace.append(
                _trace_event("discovery", "No providers found — pipeline aborted", 0, "error")
            )
            goal.status = "FAILED"
            goal.trace = list(trace)
            db.commit()
            return

        # ── Step 3: Provider Agents (generate opening offers) ───────────────
        t0 = time.monotonic()
        all_offers = []
        providers_by_id: dict[int, ProviderOut] = {}
        any_fallback = False

        for disc in discovery_results:
            for prov in disc.providers:
                providers_by_id[prov.id] = prov
                agent = ProviderAgent(prov)
                offer, fb = agent.generate_offer(disc.need_key)
                all_offers.append(offer)
                if fb:
                    any_fallback = True

        ms = int((time.monotonic() - t0) * 1000)
        trace.append(
            _trace_event(
                "provider_agents",
                f"Generated {len(all_offers)} opening offer(s)",
                ms,
                "fallback" if any_fallback else "ok",
                any_fallback,
            )
        )
        goal.trace = list(trace)
        db.commit()

        # Persist opening offers to DB
        db_offers: list[Offer] = []
        for offer in all_offers:
            db_offer = Offer(
                goal_id=goal.id,
                provider_id=offer.provider_id,
                need_key=offer.need_key,
                round=0,
                price_minor=offer.price_minor,
                scope=offer.scope,
                timeline_days=offer.timeline_days,
                status="OPENING",
            )
            db.add(db_offer)
            db_offers.append(db_offer)
        db.commit()

        # ── Step 4: Negotiation ─────────────────────────────────────────────
        t0 = time.monotonic()
        negotiated = negotiate_all(all_offers, providers_by_id)
        ms = int((time.monotonic() - t0) * 1000)

        savings = sum(
            all_offers[i].price_minor - negotiated[i].final_price_minor
            for i in range(len(negotiated))
        )
        trace.append(
            _trace_event(
                "negotiation",
                f"Negotiated {len(negotiated)} offer(s); saved {savings} minor units total",
                ms,
                "ok",
            )
        )
        goal.trace = list(trace)
        db.commit()

        # Update offers in DB to FINAL status
        for neg, db_offer in zip(negotiated, db_offers):
            db_offer.price_minor = neg.final_price_minor
            db_offer.round = neg.rounds
            db_offer.status = "FINAL"
        db.commit()

        # ── Step 5: Plan Generator ──────────────────────────────────────────
        t0 = time.monotonic()

        # Group negotiated offers by need_key
        neg_by_need: dict[str, list[NegotiatedOffer]] = {}
        for neg in negotiated:
            neg_by_need.setdefault(neg.need_key, []).append(neg)

        result = generate_plan(
            parsed.needs,
            neg_by_need,
            providers_by_id,
            goal.budget_minor,
            goal.currency,
        )
        ms = int((time.monotonic() - t0) * 1000)

        if result is None:
            trace.append(
                _trace_event(
                    "plan_generator",
                    "Could not build a plan within budget",
                    ms,
                    "error",
                )
            )
            goal.status = "FAILED"
            goal.trace = list(trace)
            db.commit()
            return

        generated_plan, fb = result
        trace.append(
            _trace_event(
                "plan_generator",
                f"Plan generated: {len(generated_plan.items)} item(s), "
                f"total {generated_plan.total_minor} {generated_plan.currency}, "
                f"score={generated_plan.score:.3f}",
                ms,
                "fallback" if fb else "ok",
                fb,
            )
        )

        # Mark selected offers in DB
        selected_provider_ids = {item.provider_id for item in generated_plan.items}
        for db_offer in db_offers:
            if db_offer.provider_id in selected_provider_ids:
                db_offer.status = "SELECTED"
        db.commit()

        # Assign real offer IDs to plan items
        offer_by_provider: dict[int, int] = {
            o.provider_id: o.id
            for o in db_offers
            if o.status == "SELECTED"
        }
        for item in generated_plan.items:
            item.offer_id = offer_by_provider.get(item.provider_id, 0)

        # Persist the plan
        plan = Plan(
            goal_id=goal.id,
            items=[i.model_dump() for i in generated_plan.items],
            total_minor=generated_plan.total_minor,
            currency=generated_plan.currency,
            rationale=generated_plan.rationale,
            status="DRAFT",
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        goal.status = "PLANNED"
        goal.trace = list(trace)
        db.commit()

        logger.info("Pipeline complete for goal %d → plan %d", goal.id, plan.id)
