"""Pydantic models = the frozen API contract (work-division doc section 2) plus internal
agent/LLM data shapes. Money is always integer minor units.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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
    key: str  # unique per goal, e.g. "catering", "photography"
    category: str  # provider category to search
    quantity: int | None = None
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


# --------------------------------------------------------------------------- requests


class GoalCreate(BaseModel):
    raw_text: str = Field(min_length=5, max_length=4000)
    budget_minor: int = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    scenario: Scenario | None = None


class ApproveRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")  # untrusted extra fields are dropped
    acknowledged_flags: list[str] = Field(default_factory=list)


class PayRequest(BaseModel):
    """/pay takes no trusted input. Any amount/verdict a client sends is ignored."""

    model_config = ConfigDict(extra="ignore")


class CaptureRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    paypal_order_id: str = Field(min_length=1, max_length=64)


# --------------------------------------------------------------------------- responses


class GoalCreated(BaseModel):
    id: int
    status: GoalStatus


class GoalOut(BaseModel):
    id: int
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
    price_minor: int
    counter_minor: int | None = None
    status: OfferStatus
    scope: str = ""


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
    price_minor: int
    timeline_days: int
    verified: bool
    currency: str = "USD"


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


class PayResponse(BaseModel):
    plan_id: int
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


class ProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    category: str
    base_price_minor: int
    min_price_minor: int
    concession_rate: float
    rating: float
    turnaround_days: int
    verified: bool
    currency: str = "USD"
    persona: str = ""
    demo: bool = True


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
    price_minor: int
    counter_minor: int | None = None
    timeline_days: int
    scope: str = ""
    status: OfferStatus = OfferStatus.OPEN


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

