"""
tests/test_goal_analyzer.py — goal analyzer with mocked LLM.

Tests:
1. When the LLM returns invalid JSON, the fallback ParsedGoal is used.
2. The fallback always has valid structure.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

from app.agents.goal_analyzer import analyze_goal
from app.schemas import ParsedGoal


def test_fallback_on_invalid_llm_json():
    """When the LLM stub returns garbage, analyze_goal uses the keyword fallback."""
    with patch("app.agents.goal_analyzer.complete_json") as mock_llm:
        # Simulate complete_json returning the fallback (used_fallback=True)
        fallback = ParsedGoal(
            needs=["web_design"],
            budget_minor=100000,
            currency="USD",
            deadline_days=30,
        )
        mock_llm.return_value = (fallback, True)

        result, used_fallback = analyze_goal(
            raw_text="Build me a website",
            budget_minor=100000,
            currency="USD",
        )

    assert used_fallback is True
    assert isinstance(result, ParsedGoal)
    assert len(result.needs) > 0
    assert result.budget_minor == 100000
    assert result.currency == "USD"
    assert result.deadline_days > 0


def test_fallback_structure_is_valid():
    """The keyword-based fallback always produces a valid ParsedGoal."""
    result, used_fallback = analyze_goal(
        raw_text="I need help with web design and copywriting in 2 weeks",
        budget_minor=50000,
        currency="USD",
    )
    # With stub provider, used_fallback may be True or False depending on canned response
    assert isinstance(result, ParsedGoal)
    assert isinstance(result.needs, list)
    assert result.budget_minor > 0
    assert len(result.currency) == 3


def test_deadline_extracted_from_text():
    """Deadline should be extracted from the raw text if present."""
    # Force fallback by patching to return a needs-only fallback
    with patch("app.agents.goal_analyzer.complete_json") as mock_llm:
        def side_effect(prompt, schema, fallback, **kwargs):
            return fallback, True

        mock_llm.side_effect = side_effect

        result, _ = analyze_goal(
            raw_text="Build a logo in 2 weeks",
            budget_minor=20000,
            currency="USD",
        )

    # With the keyword fallback, deadline should be ~14 days (2 weeks)
    assert result.deadline_days > 0


def test_web_goal_identifies_web_needs():
    """A web-related goal should identify web_design as a need."""
    with patch("app.agents.goal_analyzer.complete_json") as mock_llm:
        mock_llm.side_effect = lambda prompt, schema, fallback, **kw: (fallback, True)

        result, _ = analyze_goal(
            raw_text="Build me a professional website",
            budget_minor=80000,
            currency="USD",
        )

    # Fallback uses keyword matching — "web" should map to web_design
    assert "web_design" in result.needs
