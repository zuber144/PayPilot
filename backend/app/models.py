"""SQLAlchemy tables (work-division doc 3.8). Money columns are integer minor units."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

JSONType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), unique=True)


class Goal(Base):
    __tablename__ = "goals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    parsed: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    budget_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    scenario: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    question: Mapped[str | None] = mapped_column(Text, nullable=True)  # set when NEEDS_INPUT
    trace: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Provider(Base):
    __tablename__ = "providers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    base_price_minor: Mapped[int] = mapped_column(Integer)
    min_price_minor: Mapped[int] = mapped_column(Integer)
    concession_rate: Mapped[float] = mapped_column(Float)
    rating: Mapped[float] = mapped_column(Float)
    turnaround_days: Mapped[int] = mapped_column(Integer)
    verified: Mapped[bool] = mapped_column(Boolean)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    persona: Mapped[str] = mapped_column(Text, default="")


class Offer(Base):
    """One row per provider per negotiation round (round 0 = opening offer)."""

    __tablename__ = "offers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"), index=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"))
    need_key: Mapped[str] = mapped_column(String(50))
    round: Mapped[int] = mapped_column(Integer)
    price_minor: Mapped[int] = mapped_column(Integer)
    counter_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)  # our counter this round
    scope: Mapped[str] = mapped_column(Text, default="")
    timeline_days: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))


class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"), index=True)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONType)
    total_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    rationale: Mapped[str] = mapped_column(Text, default="")
    payguard_result: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    acknowledged_flags: Mapped[list[str]] = mapped_column(JSONType, default=list)
    status: Mapped[str] = mapped_column(String(20))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), index=True)
    paypal_order_id: Mapped[str] = mapped_column(String(64), unique=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True)  # PayPal-Request-Id
    approval_url: Mapped[str] = mapped_column(Text, default="")
    capture_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(20))
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
