"""Single gateway to the LLM (`call_json`).

Supports deterministic offline mock mode (`LLM_MODE=mock` or missing API key) and live providers
(`LLM_PROVIDER`): Grok (xAI, primary default via OpenAI-compatible endpoint), OpenAI (secondary fallback),
and Anthropic. Timeout, bounded retry on invalid JSON / schema validation error, and safe failure via
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
    if settings.LLM_PROVIDER in ("groq", "grok"):
        return settings.GROQ_API_KEY or settings.GROK_API_KEY or settings.XAI_API_KEY or settings.OPENAI_API_KEY
    if settings.LLM_PROVIDER == "openai":
        return settings.OPENAI_API_KEY
    return settings.ANTHROPIC_API_KEY


def active_provider() -> str:
    """Human-readable description of what call_json will use. Never includes the key."""
    if settings.LLM_MODE == "mock":
        return "mock (LLM_MODE=mock)"
    if settings.LLM_PROVIDER in ("groq", "grok"):
        groq_key = settings.GROQ_API_KEY or settings.GROK_API_KEY or settings.XAI_API_KEY
        if groq_key:
            model = settings.GROQ_MODEL if settings.GROQ_API_KEY or settings.LLM_PROVIDER == "groq" else settings.GROK_MODEL
            return f"groq:{model}"
        if settings.OPENAI_API_KEY:
            return f"openai:{settings.OPENAI_MODEL} (secondary fallback from groq)"
        return "mock (LLM_MODE=live but no API key for groq or openai)"
    if settings.LLM_PROVIDER == "openai":
        if settings.OPENAI_API_KEY:
            return f"openai:{settings.OPENAI_MODEL}"
        return "mock (LLM_MODE=live but no API key for openai)"
    if settings.LLM_PROVIDER == "anthropic":
        if settings.ANTHROPIC_API_KEY:
            return f"anthropic:{settings.ANTHROPIC_MODEL} (effort={settings.ANTHROPIC_EFFORT})"
        return "mock (LLM_MODE=live but no API key for anthropic)"
    return f"unknown:{settings.LLM_PROVIDER}"


def _raw_completion(system: str, user: str, task: str) -> str:
    """Raw string completion transport. Monkeypatchable in tests across both mock and live modes."""
    if settings.LLM_MODE == "mock" or not _provider_key():
        return json.dumps(llm_mock.respond(task, system, user))
    if settings.LLM_PROVIDER in ("groq", "grok"):
        key = settings.GROQ_API_KEY or settings.GROK_API_KEY or settings.XAI_API_KEY
        if key:
            try:
                return _groq_completion(system, user)
            except Exception:
                # Primary (Groq) failed: fall back to secondary (OpenAI) if key available
                if settings.OPENAI_API_KEY:
                    return _openai_completion(system, user)
                raise
        elif settings.OPENAI_API_KEY:
            return _openai_completion(system, user)
    elif settings.LLM_PROVIDER == "openai":
        return _openai_completion(system, user)
    elif settings.LLM_PROVIDER == "anthropic":
        return _anthropic_completion(system, user, _current_schema.get())
    return json.dumps(llm_mock.respond(task, system, user))


def _groq_completion(system: str, user: str) -> str:
    import httpx

    key = settings.GROQ_API_KEY or settings.GROK_API_KEY or settings.XAI_API_KEY
    base_url = settings.GROQ_BASE_URL if settings.GROQ_API_KEY or settings.LLM_PROVIDER == "groq" else settings.GROK_BASE_URL
    model = settings.GROQ_MODEL if settings.GROQ_API_KEY or settings.LLM_PROVIDER == "groq" else settings.GROK_MODEL
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system + "\n\nRespond with a single valid JSON object only."},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
    }
    with httpx.Client(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            raise ValueError("Empty completion content from Groq")
        return content


# Alias for backward compatibility
_grok_completion = _groq_completion


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
    import httpx

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.OPENAI_MODEL,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
    }
    with httpx.Client(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content")
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
