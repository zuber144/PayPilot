"""Live LLM smoke test: one real call per task through call_json (Anthropic by default).

Skipped unless the selected provider's API key is available. Proves the live path returns
schema-valid output rather than silently falling back to the deterministic templates.
"""

import json

import pytest

from app import llm
from app.agents import goal_agent
from app.config import Settings, settings
from app.schemas import (
    GoalLLMOut,
    NegotiationTextLLMOut,
    OfferTextLLMOut,
    RationaleLLMOut,
    RiskLLMOut,
    RouteLLMOut,
)

_live = Settings()  # fresh read of env / .env, unaffected by the offline autouse fixture
_KEY = _live.ANTHROPIC_API_KEY if _live.LLM_PROVIDER == "anthropic" else _live.OPENAI_API_KEY

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not _KEY, reason=f"no API key for LLM provider '{_live.LLM_PROVIDER}'"),
]

GOAL = "Corporate event in Bangalore: catering for 100 people and a photographer, event in 10 days"


@pytest.fixture(autouse=True)
def _live_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LLM_MODE", "live")
    monkeypatch.setattr(settings, "LLM_PROVIDER", _live.LLM_PROVIDER)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", _live.ANTHROPIC_API_KEY)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", _live.OPENAI_API_KEY)


def test_live_goal_agent_parses_without_fallback() -> None:
    res = goal_agent.run(GOAL, "INR")
    assert res.fallback is False, res.reason
    assert res.parsed is not None
    categories = {n.category for n in res.parsed.needs}
    assert {"catering", "photography"} <= categories, categories


@pytest.mark.parametrize(
    ("task", "schema", "user"),
    [
        ("goal_parse", GoalLLMOut, {"raw_text": GOAL, "currency": "INR"}),
        ("route", RouteLLMOut, {"node": "after_discovery", "allowed": ["continue", "retry_discovery"]}),
        ("offer_text", OfferTextLLMOut, {"provider": "ABC Catering", "need": "catering for 100"}),
        ("negotiation_text", NegotiationTextLLMOut, {"provider": "Studio X", "counter_minor": 1_600_000}),
        ("plan_rationale", RationaleLLMOut, {"items": ["ABC Catering", "Studio X"], "total_minor": 4_096_666}),
        ("risk", RiskLLMOut, {"goal": GOAL, "total_minor": 4_096_666, "budget_minor": 5_000_000}),
    ],
)
def test_live_call_json_every_task(task: str, schema: type, user: dict) -> None:
    system = f"You are a component of an event-planning agent. Task: {task}. Produce the requested JSON."
    out = llm.call_json(system, json.dumps(user), schema, task=task)
    assert isinstance(out, schema)
    if task == "route":
        assert out.action in user["allowed"]
