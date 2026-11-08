"""
app/agents/provider_agent.py — Step 3: per-provider quote generation.

ONE ProviderAgent class, instantiated per provider.
- Price is computed deterministically from base_price, min_price, concession_rate.
- The LLM writes only the pitch text (stub returns canned text).
"""
from __future__ import annotations

from app.llm import complete_json
from app.schemas import ProviderOffer, ProviderOut
from pydantic import BaseModel


class _PitchResponse(BaseModel):
    pitch: str


_FALLBACK_PITCH = _PitchResponse(
    pitch="We deliver outstanding results on time and within budget. "
          "Our experienced team is ready to exceed your expectations."
)


class ProviderAgent:
    """Generates an initial offer for a single provider."""

    def __init__(self, provider: ProviderOut) -> None:
        self.provider = provider

    def _compute_opening_price(self) -> int:
        """
        Opening price = base_price * (1 - concession_rate / 2).
        This leaves room to negotiate down to min_price.
        Price is clamped to [min_price_minor, base_price_minor].
        """
        p = self.provider
        opening = int(p.base_price_minor * (1 - p.concession_rate / 2))
        return max(p.min_price_minor, min(opening, p.base_price_minor))

    def _get_pitch(self, need_key: str) -> tuple[str, bool]:
        """Ask the LLM for a pitch string (stub returns canned text)."""
        # TODO(llm-owner): craft a real prompt that includes the provider persona,
        # the need_key, and asks for a 2-3 sentence pitch tailored to the client.
        prompt = (
            f"pitch\n"
            f"You are {self.provider.name}, a provider specialising in {self.provider.category}. "
            f"Write a 2-sentence pitch for the client's need: {need_key}. "
            f"Be confident and professional. Output JSON: {{\"pitch\": \"...\"}}."
        )
        result, used_fallback = complete_json(prompt, _PitchResponse, _FALLBACK_PITCH)
        return result.pitch, used_fallback

    def generate_offer(self, need_key: str) -> tuple[ProviderOffer, bool]:
        """Generate an opening offer for the given need."""
        price = self._compute_opening_price()
        pitch, used_fallback = self._get_pitch(need_key)

        offer = ProviderOffer(
            provider_id=self.provider.id,
            need_key=need_key,
            price_minor=price,
            scope=f"Full {need_key.replace('_', ' ')} service as described",
            timeline_days=self.provider.turnaround_days,
            pitch=pitch,
        )
        return offer, used_fallback
