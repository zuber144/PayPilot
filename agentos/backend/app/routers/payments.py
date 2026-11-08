"""
app/routers/payments.py — capture webhook and transaction listing.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Transaction
from app.payments.service import capture_payment
from app.schemas import CaptureRequest, CaptureResponse, TransactionOut

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/capture")
def capture(body: CaptureRequest, db: Session = Depends(get_db)) -> CaptureResponse:
    """
    Called by the frontend after PayPal redirects back.
    The token from the return URL is the PayPal order ID.
    """
    return capture_payment(body.token, db)


@router.get("/transactions")
def list_transactions(db: Session = Depends(get_db)) -> list[TransactionOut]:
    txns = db.query(Transaction).order_by(Transaction.created_at.desc()).all()
    return [TransactionOut.model_validate(t) for t in txns]
