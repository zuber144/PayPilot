"""
app/routers/providers.py — provider listing.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Provider
from app.schemas import ProviderOut

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("")
def list_providers(db: Session = Depends(get_db)) -> list[ProviderOut]:
    providers = db.query(Provider).order_by(Provider.rating.desc()).all()
    return [ProviderOut.model_validate(p) for p in providers]
