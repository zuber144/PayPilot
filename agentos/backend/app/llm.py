"""
app/llm.py — provider-agnostic LLM wrapper.

complete_json(prompt, schema, fallback) calls the configured provider,
validates the response against `schema` (a Pydantic model class),
and returns the fallback value on any failure.

Providers:
  stub  — returns canned JSON without any network call (DEFAULT for local dev)
  openai — TODO(llm-owner): implement real OpenAI call
  anthropic — TODO(llm-owner): implement real Anthropic call
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# ---------------------------------------------------------------------------
# Stub provider — canned responses keyed on prompt keywords
# ---------------------------------------------------------------------------

_STUB_RESPONSES: dict[str, dict[str, Any]] = {
    "goal_analyzer": {
        "needs": ["web_design", "copywriting"],
        "budget_minor": 500000,
        "currency": "USD",
        "deadline_days": 30,
    },
    "pitch": {
        "pitch": "We deliver high-quality work on time with a satisfaction guarantee. "
                 "Our team has 5+ years of experience in this domain."
    },
    "rationale": {
        "rationale": "Selected providers offer the best balance of quality, price, and speed "
                     "within your budget. All vendors are verified and highly rated."
    },
}


def _stub_complete(prompt: str) -> dict[str, Any]:
    """Return a canned response based on the prompt keywords and context."""
    lower = prompt.lower()
    if "goal_analyzer" in lower:
        needs = []
        if "web" in lower:
            needs.append("web_design")
        if "logo" in lower:
            needs.append("logo_design")
        if "copy" in lower or "content" in lower or "blog" in lower:
            needs.append("copywriting")
        elif "market" in lower:
            needs.append("marketing")
        if not needs:
            needs = ["web_design", "copywriting"]

        return {
            "needs": needs,
            "budget_minor": 200000,
            "currency": "USD",
            "deadline_days": 21,
        }

    for key, data in _STUB_RESPONSES.items():
        if key in lower:
            return data
    # generic fallback
    return {"result": "stub response — no keyword matched"}


# ---------------------------------------------------------------------------
# OpenAI provider (placeholder)
# ---------------------------------------------------------------------------

def _openai_complete(prompt: str, timeout: float) -> dict[str, Any]:
    # TODO(llm-owner): implement real OpenAI chat completion call.
    # 1. Build messages=[{"role":"user","content": prompt}]
    # 2. POST https://api.openai.com/v1/chat/completions with
    #    model=settings.llm_model, response_format={"type":"json_object"}
    # 3. Return json.loads(response.choices[0].message.content)
    raise NotImplementedError("OpenAI provider not yet implemented")


# ---------------------------------------------------------------------------
# Anthropic provider (placeholder)
# ---------------------------------------------------------------------------

def _anthropic_complete(prompt: str, timeout: float) -> dict[str, Any]:
    # TODO(llm-owner): implement real Anthropic messages call.
    # 1. POST https://api.anthropic.com/v1/messages
    # 2. Parse the text block from content[0].text as JSON
    raise NotImplementedError("Anthropic provider not yet implemented")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def complete_json(
    prompt: str,
    schema: Type[T],
    fallback: T,
    *,
    timeout: float = 20.0,
    retries: int = 1,
) -> tuple[T, bool]:
    """
    Call the configured LLM and return a validated Pydantic instance.

    Returns (result, used_fallback).
    On any failure (network, timeout, invalid JSON, schema mismatch) the fallback
    is returned and used_fallback=True is set so callers can record it in the trace.
    """
    settings = get_settings()
    provider = settings.llm_provider.lower()

    for attempt in range(retries + 1):
        try:
            if provider == "stub":
                raw = _stub_complete(prompt)
            elif provider == "openai":
                raw = _openai_complete(prompt, timeout)
            elif provider == "anthropic":
                raw = _anthropic_complete(prompt, timeout)
            else:
                # TODO(llm-owner): add your custom provider here
                logger.warning("Unknown LLM provider %r — using stub", provider)
                raw = _stub_complete(prompt)

            validated = schema.model_validate(raw)
            return validated, False

        except NotImplementedError:
            # Provider not implemented — immediately use fallback
            logger.warning("LLM provider %r not implemented; using fallback", provider)
            return fallback, True

        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            logger.warning("LLM call attempt %d failed: %s", attempt + 1, exc)
            if attempt >= retries:
                break

        except (json.JSONDecodeError, ValidationError, KeyError) as exc:
            logger.warning("LLM response invalid on attempt %d: %s", attempt + 1, exc)
            if attempt >= retries:
                break

        except Exception as exc:
            logger.error("Unexpected LLM error: %s", exc)
            break

        time.sleep(0.5)  # brief pause before retry

    logger.info("Using fallback for LLM call")
    return fallback, True
