"""Payments router: POST /payments/capture, GET /transactions."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Transaction
from app.payments import service as payment_service
from app.schemas import CaptureRequest, TransactionOut

router = APIRouter(tags=["payments"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/payments/capture", response_model=TransactionOut)
def capture_payment(
    body: CaptureRequest,
    db: DbSession,
) -> TransactionOut:
    return payment_service.capture(db, body.paypal_order_id)


@router.get("/transactions", response_model=list[TransactionOut])
def list_transactions(db: DbSession) -> list[TransactionOut]:
    txns = db.scalars(
        select(Transaction).order_by(Transaction.created_at.desc(), Transaction.id.desc())
    ).all()
    return [payment_service.transaction_to_out(db, t) for t in txns]
