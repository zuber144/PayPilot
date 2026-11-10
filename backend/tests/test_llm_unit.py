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


def test_llm_mock_goal_parse_catering_and_photography() -> None:
    user = json.dumps(
        {
            "raw_text": "Corporate event in Bangalore: catering for 100 people and a photographer, event in 10 days",
            "currency": "INR",
        }
    )
    out = call_json("sys", user, GoalLLMOut, task="goal_parse")
    assert [n.key for n in out.needs] == ["catering", "photography"]
    assert out.needs[0].quantity == 100
    assert out.deadline_days == 10
    assert out.currency == "INR"
    assert out.question is None


def test_llm_mock_goal_parse_vague_returns_question() -> None:
    user = json.dumps({"raw_text": "Something nice for our office", "currency": "INR"})
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
        json.dumps({"provider_name": "ABC Catering", "category": "catering", "turnaround_days": 7}),
        OfferTextLLMOut,
        task="offer_text",
    )
    assert "ABC Catering" in offer_out.scope

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

    def fake_raw(system: str, user: str, task: str) -> str:
        raise TimeoutError(f"Request timed out using {secret}")

    monkeypatch.setattr(llm, "_raw_completion", fake_raw)
    with pytest.raises(LLMFailure) as exc_info:
        call_json("sys", "{}", RouteLLMOut, task="route")
    assert secret not in str(exc_info.value)


def test_llm_mock_unsupported_task_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported LLM task"):
        llm_mock.respond("unknown_task", "sys", "{}")
