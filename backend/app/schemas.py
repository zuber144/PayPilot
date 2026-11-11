"""Pydantic models = the frozen API contract (work-division doc section 2) plus internal
agent/LLM data shapes. Money is always integer minor units.

Product-comparison pivot (DECISIONS.md #18): a "provider" is one store listing (Amazon/Flipkart
product). `*_minor` fields are USD cents (the charge currency); `original_*` fields are the
listing's native INR paise, for display only.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.enums import (
    GoalStatus,
    OfferStatus,
    PlanStatus,
    RuleOutcome,
    Scenario,
    TraceNode,
    TraceStatus,
    TxnStatus,
    Verdict,
)

# --------------------------------------------------------------------------- shared


class Need(BaseModel):
    key: str  # unique per goal, e.g. "party_hats", "balloons"
    category: str  # product category / search term
    quantity: int | None = None  # units wanted (None = one pack)
    must_haves: list[str] = Field(default_factory=list)


class ParsedGoal(BaseModel):
    needs: list[Need]
    deadline_days: int | None = None
    currency: str


class TraceEvent(BaseModel):
    seq: int
    ts: datetime
    node: TraceNode
    action: str
    status: TraceStatus
    summary: str
    reason: str = ""
    duration_ms: int = 0
    data: dict[str, Any] = Field(default_factory=dict)

    # Legacy (agentos/backend) aliases, derived; see DECISIONS.md #19.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def step(self) -> str:
        return f"{self.node.value}:{self.action}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def used_fallback(self) -> bool:
        return self.status == TraceStatus.FALLBACK


# --------------------------------------------------------------------------- requests


class GoalCreate(BaseModel):
    raw_text: str = Field(min_length=5, max_length=4000)
    budget_minor: int = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    scenario: Scenario | None = None
    user_id: int | None = None  # legacy clients send this; stored only if the user exists


class ApproveRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")  # untrusted extra fields are dropped
    acknowledged_flags: list[str] = Field(default_factory=list)


class PayRequest(BaseModel):
    """/pay takes no trusted input. Any amount/verdict a client sends is ignored."""

    model_config = ConfigDict(extra="ignore")


class CaptureRequest(BaseModel):
    """`paypal_order_id`, or the legacy `{token, plan_id}` body (token = PayPal order id from the
    return URL). When plan_id is given it must match the order's plan."""

    model_config = ConfigDict(extra="ignore")
    paypal_order_id: str | None = Field(default=None, min_length=1, max_length=64)
    token: str | None = Field(default=None, min_length=1, max_length=64)
    plan_id: int | None = None

    @model_validator(mode="after")
    def _require_order_id(self) -> "CaptureRequest":
        if not (self.paypal_order_id or self.token):
            raise ValueError("paypal_order_id (or legacy token) is required")
        if self.paypal_order_id and self.token and self.paypal_order_id != self.token:
            raise ValueError("paypal_order_id and token disagree")
        return self

    @property
    def order_id(self) -> str:
        return self.paypal_order_id or self.token or ""


# --------------------------------------------------------------------------- responses


class GoalCreated(BaseModel):
    id: int
    status: GoalStatus


class GoalOut(BaseModel):
    id: int
    user_id: int | None = None
    status: GoalStatus
    raw_text: str
    budget_minor: int
    currency: str
    scenario: Scenario | None = None
    parsed: ParsedGoal | None = None
    question: str | None = None
    trace: list[TraceEvent] = Field(default_factory=list)
    plan_id: int | None = None
    created_at: datetime


class OfferRound(BaseModel):
    round: int
    price_minor: int  # line total: packs * pack price + shipping (USD cents)
    counter_minor: int | None = None
    status: OfferStatus
    scope: str = ""
    packs: int = 1
    shipping_minor: int = 0
    tags: list[str] = Field(default_factory=list)  # BEST_PRICE, FASTEST_DELIVERY, TOP_RATED


class ProviderOffers(BaseModel):
    provider_id: int
    provider_name: str
    verified: bool
    rating: float
    timeline_days: int
    opening_price_minor: int
    final_price_minor: int
    status: OfferStatus  # status of the latest round
    rounds: list[OfferRound]
    store: str = ""
    product_title: str = ""
    url: str = ""
    pack_size: int = 1
    review_count: int = 0
    tags: list[str] = Field(default_factory=list)  # tags of the latest round
    original_currency: str = "INR"
    original_price_minor: int = 0  # native pack price (paise), display only


class OfferFlatOut(BaseModel):
    """One offer row (legacy agentos/backend flat offers shape)."""

    id: int
    goal_id: int
    provider_id: int
    need_key: str
    round: int
    price_minor: int
    scope: str
    timeline_days: int
    status: OfferStatus
    packs: int = 1
    shipping_minor: int = 0
    tags: list[str] = Field(default_factory=list)


class OfferGroup(BaseModel):
    need_key: str
    offers: list[ProviderOffers]


class OffersOut(BaseModel):
    goal_id: int
    groups: list[OfferGroup]


class PlanItem(BaseModel):
    need_key: str
    provider_id: int
    provider_name: str
    price_minor: int  # line total in USD cents = packs * pack_price_minor + shipping_minor
    timeline_days: int
    verified: bool
    currency: str = "USD"
    store: str = ""
    product_title: str = ""
    url: str = ""
    quantity: int | None = None
    packs: int = 1
    pack_price_minor: int = 0
    shipping_minor: int = 0
    original_currency: str = "INR"
    original_price_minor: int = 0  # native line total (paise), display only
    scope: str = ""  # listing summary (legacy field)
    offer_id: int | None = None  # selected offer row (legacy field)


class RuleResult(BaseModel):
    id: str  # RuleId value
    result: RuleOutcome
    detail: str


class Flag(BaseModel):
    id: str
    source: str  # "POLICY" or "AI"
    message: str
    requires_ack: bool = False


class PayGuardResult(BaseModel):
    verdict: Verdict
    risk_score: float | None = None
    ai_ok: bool
    flags: list[Flag] = Field(default_factory=list)
    rules: list[RuleResult]
    checked_at: datetime | None = None


class LegacyRuleResult(BaseModel):
    """agentos/backend rule shape: {rule, passed, severity, reason}."""

    rule: str
    passed: bool
    severity: str  # BLOCK | REVIEW
    reason: str


class LegacyPayGuardResult(BaseModel):
    """agentos/backend PayGuard shape, derived from PayGuardResult (read-only view)."""

    verdict: Verdict
    rules: list[LegacyRuleResult]
    risk_score: int | None = None  # 0-100
    flags: list[str] = Field(default_factory=list)
    summary: str = ""

    @classmethod
    def from_result(cls, pg: "PayGuardResult") -> "LegacyPayGuardResult":
        review_class = {"AI_RISK_MEDIUM", "SINGLE_VENDOR_SHARE"}
        rules = [
            LegacyRuleResult(
                rule=r.id,
                passed=r.result == RuleOutcome.PASS,
                severity=(
                    r.result.value
                    if r.result != RuleOutcome.PASS
                    else ("REVIEW" if r.id in review_class else "BLOCK")
                ),
                reason=r.detail,
            )
            for r in pg.rules
        ]
        blocking = sum(1 for r in pg.rules if r.result == RuleOutcome.BLOCK)
        review = sum(1 for r in pg.rules if r.result == RuleOutcome.REVIEW)
        return cls(
            verdict=pg.verdict,
            rules=rules,
            risk_score=None if pg.risk_score is None else round(pg.risk_score * 100),
            flags=[f.id for f in pg.flags],
            summary=(
                f"{pg.verdict.value}: {blocking} blocking rule(s), {review} needing review"
                + ("" if pg.ai_ok else "; AI risk check unavailable")
            ),
        )


class PlanOut(BaseModel):
    id: int
    goal_id: int
    status: PlanStatus
    currency: str
    total_minor: int
    budget_minor: int
    rationale: str
    items: list[PlanItem]
    payguard: PayGuardResult | None = None
    acknowledged_flags: list[str] = Field(default_factory=list)
    approved_at: datetime | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def payguard_result(self) -> LegacyPayGuardResult | None:
        """Legacy (agentos/backend) view of `payguard`; derived, never stored."""
        return LegacyPayGuardResult.from_result(self.payguard) if self.payguard else None


class PayResponse(BaseModel):
    plan_id: int
    transaction_id: int | None = None
    paypal_order_id: str
    approval_url: str
    status: PlanStatus
    reused: bool = False


class TransactionOut(BaseModel):
    id: int
    plan_id: int
    goal_id: int | None = None
    goal_summary: str | None = None
    paypal_order_id: str
    capture_id: str | None = None
    amount_minor: int
    currency: str
    status: TxnStatus
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def transaction_id(self) -> int:
        return self.id


class ProviderOut(BaseModel):
    """One store listing. base_price_minor = min_price_minor = one pack in USD cents (fixed price)."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str  # seller display name, e.g. "PartyZone Official (Flipkart)"
    category: str
    base_price_minor: int
    min_price_minor: int
    concession_rate: float = 0.0
    rating: float
    turnaround_days: int  # delivery days
    verified: bool
    currency: str = "USD"
    persona: str = ""
    demo: bool = True
    listing_key: str = ""
    store: str = ""
    product_title: str = ""
    url: str = ""
    pack_size: int = 1
    shipping_minor: int = 0
    review_count: int = 0
    original_currency: str = "INR"
    original_price_minor: int = 0  # pack price, paise
    original_shipping_minor: int = 0  # paise
    source: str = "catalog"  # "catalog" (seeded/offline) or "live" (scraped)


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorEnvelope(BaseModel):
    error: ErrorBody


# --------------------------------------------------------------------------- internal agent shapes


class Filters(BaseModel):
    """Preference filters. Verification is NOT a filter: it is never relaxed."""

    min_rating: float | None = None
    max_turnaround_days: int | None = None
    price_ceiling_minor: int | None = None


class CoverageReport(BaseModel):
    counts: dict[str, int]  # need_key -> verified candidates found
    required: int
    sufficient: bool  # every need >= required
    minimum_met: bool  # every need >= MIN_COVERAGE


class OfferDraft(BaseModel):
    need_key: str
    provider_id: int
    round: int
    price_minor: int  # line total in USD cents, computed in code
    counter_minor: int | None = None
    timeline_days: int
    scope: str = ""
    status: OfferStatus = OfferStatus.OPEN
    quantity: int | None = None
    packs: int = 1
    pack_price_minor: int = 0
    shipping_minor: int = 0
    tags: list[str] = Field(default_factory=list)


class PlanDraft(BaseModel):
    items: list[PlanItem]
    total_minor: int
    currency: str
    rationale: str = ""


# --------------------------------------------------------------------------- LLM output schemas


class GoalLLMOut(BaseModel):
    needs: list[Need] = Field(default_factory=list)
    deadline_days: int | None = None
    currency: str | None = None
    question: str | None = None  # set by the model if the goal is too vague


class RouteLLMOut(BaseModel):
    action: str
    reason: str = ""


class OfferTextLLMOut(BaseModel):
    scope: str
    pitch: str = ""


class NegotiationTextLLMOut(BaseModel):
    message: str


class RationaleLLMOut(BaseModel):
    rationale: str


class RiskFlagLLM(BaseModel):
    id: str
    message: str


class RiskLLMOut(BaseModel):
    risk_score: float = Field(ge=0.0, le=1.0)
    flags: list[RiskFlagLLM] = Field(default_factory=list)

