"""
app/schemas.py — Pydantic v2 request/response models shared across modules.
"""
from __future__ import annotations

import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Shared error envelope
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

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
    persona: str


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------

class GoalCreate(BaseModel):
    raw_text: str = Field(..., min_length=5)
    budget_minor: int = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    user_id: int = Field(default=1)


class TraceEvent(BaseModel):
    step: str
    summary: str
    duration_ms: int
    status: str  # ok | error | fallback
    used_fallback: bool = False


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    raw_text: str
    parsed: Optional[dict[str, Any]] = None
    budget_minor: int
    currency: str
    status: str
    trace: List[dict[str, Any]] = []
    created_at: datetime.datetime
    plan_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Offers
# ---------------------------------------------------------------------------

class OfferOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    goal_id: int
    provider_id: int
    need_key: str
    round: int
    price_minor: int
    scope: str
    timeline_days: int
    status: str


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------

class PlanItem(BaseModel):
    need_key: str
    provider_id: int
    provider_name: str
    price_minor: int
    scope: str
    timeline_days: int
    offer_id: int


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    goal_id: int
    items: List[dict[str, Any]]
    total_minor: int
    currency: str
    rationale: str
    payguard_result: Optional[dict[str, Any]] = None
    status: str
    approved_at: Optional[datetime.datetime] = None


class PayGuardRuleResult(BaseModel):
    rule: str
    passed: bool
    severity: str  # BLOCK | REVIEW | INFO
    reason: str


class PayGuardResult(BaseModel):
    verdict: str  # APPROVED | REVIEW | BLOCKED
    rules: List[PayGuardRuleResult]
    risk_score: Optional[int] = None
    flags: List[str] = []
    summary: str


class ApproveRequest(BaseModel):
    acknowledged_flags: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Payments / Transactions
# ---------------------------------------------------------------------------

class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    plan_id: int
    paypal_order_id: str
    capture_id: Optional[str] = None
    amount_minor: int
    currency: str
    status: str
    created_at: datetime.datetime


class PayResponse(BaseModel):
    transaction_id: int
    paypal_order_id: str
    approval_url: str
    status: str


class CaptureRequest(BaseModel):
    token: str  # PayPal order token from the return URL
    plan_id: int


class CaptureResponse(BaseModel):
    transaction_id: int
    capture_id: str
    amount_minor: int
    currency: str
    status: str


# ---------------------------------------------------------------------------
# Pipeline internals (typed contracts between agent steps)
# ---------------------------------------------------------------------------

class ParsedGoal(BaseModel):
    needs: List[str]
    budget_minor: int
    currency: str
    deadline_days: int


class DiscoveryResult(BaseModel):
    need_key: str
    providers: List[ProviderOut]


class ProviderOffer(BaseModel):
    provider_id: int
    need_key: str
    price_minor: int
    scope: str
    timeline_days: int
    pitch: str  # LLM-written pitch text (stub)


class NegotiatedOffer(BaseModel):
    provider_id: int
    need_key: str
    final_price_minor: int
    rounds: int
    accepted: bool
    scope: str
    timeline_days: int


class GeneratedPlan(BaseModel):
    items: List[PlanItem]
    total_minor: int
    currency: str
    rationale: str
    score: float
