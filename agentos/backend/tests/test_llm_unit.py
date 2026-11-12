"""Unit tests for `app.llm` and `app.llm_mock`."""

from __future__ import annotations

import json

import pytest

from app import llm, llm_mock
from app.config import settings
from app.llm import LLMFailure, call_json
from app.schemas import (
    GoalLLMOut,
    NegotiationTextLLMOut,
    OfferTextLLMOut,
    RationaleLLMOut,
    RiskLLMOut,
    RouteLLMOut,
)


def test_llm_mock_goal_parse_party_hats_and_balloons() -> None:
    user = json.dumps(
        {
            "raw_text": "Birthday party supplies: 10 party hats and 50 balloons, needed within 5 days",
            "currency": "USD",
        }
    )
    out = call_json("sys", user, GoalLLMOut, task="goal_parse")
    assert [n.key for n in out.needs] == ["party_hats", "balloons"]
    assert [n.category for n in out.needs] == ["party_hats", "balloons"]
    assert [n.quantity for n in out.needs] == [10, 50]
    assert out.deadline_days == 5
    assert out.currency == "USD"
    assert out.question is None


def test_llm_mock_goal_parse_vague_returns_question() -> None:
    user = json.dumps({"raw_text": "Something nice for our office", "currency": "USD"})
    out = call_json("sys", user, GoalLLMOut, task="goal_parse")
    assert out.needs == []
    assert out.question is not None


def test_llm_mock_other_tasks() -> None:
    route_out = call_json(
        "sys",
        json.dumps({"allowed": ["retry_discovery", "ask_user"]}),
        RouteLLMOut,
        task="route",
    )
    assert route_out.action == "retry_discovery"

    offer_out = call_json(
        "sys",
        json.dumps(
            {
                "provider_name": "PartyZone Official (Flipkart)",
                "product_title": "Pack of 10 Metallic Party Hats",
                "packs": 2,
                "turnaround_days": 4,
            }
        ),
        OfferTextLLMOut,
        task="offer_text",
    )
    assert "PartyZone Official (Flipkart)" in offer_out.scope
    assert "2 x Pack of 10 Metallic Party Hats" in offer_out.scope

    neg_out = call_json("sys", json.dumps({"round": 2}), NegotiationTextLLMOut, task="negotiation_text")
    assert "2" in neg_out.message

    rat_out = call_json("sys", "{}", RationaleLLMOut, task="plan_rationale")
    assert len(rat_out.rationale) > 10

    risk_out = call_json("sys", "{}", RiskLLMOut, task="risk")
    assert risk_out.risk_score == pytest.approx(0.1)
    assert risk_out.flags == []


def test_call_json_retries_once_on_invalid_json_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LLM_RETRIES", 1)
    calls: list[int] = []

    def fake_raw(system: str, user: str, task: str) -> str:
        calls.append(1)
        if len(calls) == 1:
            return "{not valid json"
        return json.dumps({"action": "discover", "reason": "ok on retry"})

    monkeypatch.setattr(llm, "_raw_completion", fake_raw)
    out = call_json("sys", "{}", RouteLLMOut, task="route")
    assert out.action == "discover"
    assert len(calls) == 2


def test_call_json_raises_llm_failure_after_exhausting_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LLM_RETRIES", 1)
    calls: list[int] = []

    def fake_raw(system: str, user: str, task: str) -> str:
        calls.append(1)
        return "not-json-at-all"

    monkeypatch.setattr(llm, "_raw_completion", fake_raw)
    with pytest.raises(LLMFailure):
        call_json("sys", "{}", RouteLLMOut, task="route")
    assert len(calls) == 2


def test_call_json_raises_llm_failure_on_schema_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LLM_RETRIES", 1)
    monkeypatch.setattr(llm, "_raw_completion", lambda s, u, t: json.dumps({"risk_score": 5.0}))
    with pytest.raises(LLMFailure):
        call_json("sys", "{}", RiskLLMOut, task="risk")


def test_call_json_raises_llm_failure_on_timeout_never_logs_key(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "sk-super-secret-test-key-999"
    monkeypatch.setattr(settings, "OPENAI_API_KEY", secret)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", secret)

    def fake_raw(system: str, user: str, task: str) -> str:
        raise TimeoutError(f"Request timed out using {secret}")

    monkeypatch.setattr(llm, "_raw_completion", fake_raw)
    with pytest.raises(LLMFailure) as exc_info:
        call_json("sys", "{}", RouteLLMOut, task="route")
    assert secret not in str(exc_info.value)


def test_llm_mock_unsupported_task_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported LLM task"):
        llm_mock.respond("unknown_task", "sys", "{}")


def test_groq_active_provider_and_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LLM_MODE", "live")
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")

    # With Groq key
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk-test-key")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
    assert "groq:" in llm.active_provider()
    assert llm._provider_key() == "gsk-test-key"

    # Without Groq key, with OpenAI key -> secondary fallback
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    monkeypatch.setattr(settings, "GROK_API_KEY", "")
    monkeypatch.setattr(settings, "XAI_API_KEY", "")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-openai-secondary")
    assert "openai:" in llm.active_provider()
    assert "secondary fallback" in llm.active_provider()
    assert llm._provider_key() == "sk-openai-secondary"


def test_groq_fails_falls_back_to_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LLM_MODE", "live")
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk-test-key")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-openai-secondary")

    calls: list[str] = []

    def mock_groq(s: str, u: str) -> str:
        calls.append("groq")
        raise RuntimeError("Groq API rate limit or network error")

    def mock_openai(s: str, u: str) -> str:
        calls.append("openai")
        return json.dumps({"action": "discover", "reason": "openai fallback worked"})

    monkeypatch.setattr(llm, "_groq_completion", mock_groq)
    monkeypatch.setattr(llm, "_grok_completion", mock_groq)
    monkeypatch.setattr(llm, "_openai_completion", mock_openai)

    raw = llm._raw_completion("sys", "{}", "route")
    assert calls == ["groq", "openai"]
    assert "openai fallback worked" in raw
