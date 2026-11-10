"""Single gateway to the LLM (`call_json`).

Supports deterministic offline mock mode (`LLM_MODE=mock` or missing API key) and live OpenAI JSON mode
with timeout, bounded retry on invalid JSON / schema validation error, and safe failure via `LLMFailure`.
Never logs the API key.
"""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app import llm_mock
from app.config import settings

T = TypeVar("T", bound=BaseModel)

VALID_TASKS = frozenset({"goal_parse", "route", "offer_text", "negotiation_text", "plan_rationale", "risk"})


class LLMFailure(Exception):
    """Raised when the LLM call times out, errors, or returns invalid JSON/schema after retries."""


def _raw_completion(system: str, user: str, task: str) -> str:
    """Raw string completion transport. Monkeypatchable in tests across both mock and live modes."""
    if settings.LLM_MODE == "mock" or not settings.OPENAI_API_KEY:
        return json.dumps(llm_mock.respond(task, system, user))

    from openai import OpenAI

    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        max_retries=0,
    )
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
    )
    content = response.choices[0].message.content if response.choices else None
    if not content:
        raise ValueError("Empty completion content from OpenAI")
    return content


def call_json(system: str, user: str, schema_model: type[T], *, task: str) -> T:
    """Call the LLM in JSON mode and validate the response against `schema_model`.

    Retries `settings.LLM_RETRIES` times on invalid JSON or Pydantic ValidationError.
    Transport errors or timeouts raise `LLMFailure` immediately.
    """
    if task not in VALID_TASKS:
        raise LLMFailure(f"Unsupported LLM task: {task!r}")
    attempts = 1 + max(0, int(settings.LLM_RETRIES))
    last_error: Exception | None = None

    for _ in range(attempts):
        try:
            raw = _raw_completion(system, user, task)
        except LLMFailure:
            raise
        except Exception as exc:
            raise LLMFailure(f"LLM transport failed for task '{task}': {type(exc).__name__}") from exc

        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError("LLM output must be a JSON object")
            return schema_model.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as exc:
            last_error = exc

    raise LLMFailure(
        f"LLM validation failed for task '{task}' after {attempts} attempt(s): {type(last_error).__name__}"
    ) from last_error
