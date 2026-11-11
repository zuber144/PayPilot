"""Providers router: GET /providers."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Provider
from app.schemas import ProviderOut

router = APIRouter(tags=["providers"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/providers", response_model=list[ProviderOut])
def list_providers(db: DbSession) -> list[ProviderOut]:
    providers = db.scalars(select(Provider).order_by(Provider.id.asc())).all()
    result: list[ProviderOut] = []
    for p in providers:
        out = ProviderOut.model_validate(p)
        out.demo = True
        result.append(out)
    return result
