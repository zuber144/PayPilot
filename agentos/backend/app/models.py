"""
app/models.py — 6 SQLAlchemy tables.
Money is always INTEGER minor units (cents). Never use floats.
"""
from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    goals: Mapped[list["Goal"]] = relationship("Goal", back_populates="user")


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    budget_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    # Status: NEW | RUNNING | PLANNED | FAILED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NEW")
    trace: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, nullable=False, default=list)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="goals")
    offers: Mapped[list["Offer"]] = relationship("Offer", back_populates="goal")
    plans: Mapped[list["Plan"]] = relationship("Plan", back_populates="goal")


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    base_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    min_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    concession_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.1)
    rating: Mapped[float] = mapped_column(Float, nullable=False, default=4.0)
    turnaround_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    persona: Mapped[str] = mapped_column(Text, nullable=False, default="")

    offers: Mapped[list["Offer"]] = relationship("Offer", back_populates="provider")


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"), nullable=False)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"), nullable=False)
    need_key: Mapped[str] = mapped_column(String(100), nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False, default="")
    timeline_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    # Status: OPENING | COUNTERED | FINAL | SELECTED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPENING")

    goal: Mapped["Goal"] = relationship("Goal", back_populates="offers")
    provider: Mapped["Provider"] = relationship("Provider", back_populates="offers")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"), nullable=False, unique=True)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, nullable=False, default=list)
    total_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    rationale: Mapped[str] = mapped_column(Text, nullable=False, default="")
    payguard_result: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    # Status: DRAFT | CHECKED | APPROVED | PAYING | PAID | BLOCKED | PAY_FAILED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    approved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    goal: Mapped["Goal"] = relationship("Goal", back_populates="plans")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="plan")

    __table_args__ = (
        CheckConstraint("total_minor >= 0", name="plans_total_minor_nonneg"),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)
    paypal_order_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    capture_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    # Status: CREATED | COMPLETED | FAILED | CANCELLED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CREATED")
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    plan: Mapped["Plan"] = relationship("Plan", back_populates="transactions")

    __table_args__ = (
        # Partial unique index: at most one CREATED or COMPLETED transaction per plan
        Index(
            "ix_transactions_plan_live",
            "plan_id",
            unique=True,
            postgresql_where=text("status IN ('CREATED', 'COMPLETED')"),
            sqlite_where=text("status IN ('CREATED', 'COMPLETED')"),
        ),
    )
