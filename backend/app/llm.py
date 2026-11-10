"""Single gateway to the LLM (`call_json`).

Supports deterministic offline mock mode (`LLM_MODE=mock` or missing API key) and two live providers
(`LLM_PROVIDER`): Anthropic (default, structured outputs constrained to the task's Pydantic schema) and
OpenAI JSON mode. Timeout, bounded retry on invalid JSON / schema validation error, and safe failure via
`LLMFailure`. Never logs the API key.
"""

from __future__ import annotations

import json
from contextvars import ContextVar
from typing import Any, TypeVar, cast

from pydantic import BaseModel, ValidationError

from app import llm_mock
from app.config import settings

T = TypeVar("T", bound=BaseModel)

VALID_TASKS = frozenset({"goal_parse", "route", "offer_text", "negotiation_text", "plan_rationale", "risk"})


# Schema of the in-flight call_json request, so the transport can constrain output to it
# without changing the monkeypatchable `_raw_completion(system, user, task)` signature.
_current_schema: ContextVar[type[BaseModel] | None] = ContextVar("_current_schema", default=None)


class LLMFailure(Exception):
    """Raised when the LLM call times out, errors, or returns invalid JSON/schema after retries."""


def _provider_key() -> str:
    return settings.ANTHROPIC_API_KEY if settings.LLM_PROVIDER == "anthropic" else settings.OPENAI_API_KEY


def active_provider() -> str:
    """Human-readable description of what call_json will use. Never includes the key."""
    if settings.LLM_MODE == "mock":
        return "mock (LLM_MODE=mock)"
    if not _provider_key():
        return f"mock (LLM_MODE=live but no API key for provider '{settings.LLM_PROVIDER}')"
    if settings.LLM_PROVIDER == "anthropic":
        return f"anthropic:{settings.ANTHROPIC_MODEL} (effort={settings.ANTHROPIC_EFFORT})"
    return f"openai:{settings.OPENAI_MODEL}"


def _raw_completion(system: str, user: str, task: str) -> str:
    """Raw string completion transport. Monkeypatchable in tests across both mock and live modes."""
    if settings.LLM_MODE == "mock" or not _provider_key():
        return json.dumps(llm_mock.respond(task, system, user))
    if settings.LLM_PROVIDER == "anthropic":
        return _anthropic_completion(system, user, _current_schema.get())
    return _openai_completion(system, user)


def _anthropic_completion(system: str, user: str, schema_model: type[BaseModel] | None) -> str:
    import anthropic

    client = anthropic.Anthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        max_retries=0,  # retries are bounded by call_json / settings.LLM_RETRIES
    )
    output_config: dict[str, Any] = {"effort": settings.ANTHROPIC_EFFORT}
    if schema_model is not None:
        output_config["format"] = {"type": "json_schema", "schema": anthropic.transform_schema(schema_model)}
    # No temperature: non-default sampling parameters are rejected on current models.
    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=settings.ANTHROPIC_MAX_TOKENS,
        system=system + "\n\nRespond with a single JSON object only.",
        messages=[{"role": "user", "content": user}],
        output_config=cast(Any, output_config),
    )
    if response.stop_reason in ("refusal", "max_tokens"):
        raise ValueError(f"Anthropic stop_reason={response.stop_reason}")
    text = next((b.text for b in response.content if b.type == "text"), "")
    if not text:
        raise ValueError("Empty completion content from Anthropic")
    return text


def _openai_completion(system: str, user: str) -> str:
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
        token = _current_schema.set(schema_model)
        try:
            raw = _raw_completion(system, user, task)
        except LLMFailure:
            raise
        except Exception as exc:
            raise LLMFailure(f"LLM transport failed for task '{task}': {type(exc).__name__}") from exc
        finally:
            _current_schema.reset(token)

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
