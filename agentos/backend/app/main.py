"""
app/main.py — FastAPI application entry point.

Wires up: CORS, routers, DB table creation on startup.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app import db
from app.db import Base
from app.routers import goals, payments, plans, providers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (no Alembic)
    try:
        logger.info("Creating database tables if not exists…")
        Base.metadata.create_all(bind=db.engine)
        logger.info("Database ready.")
    except Exception as exc:
        logger.warning("Could not create database tables on startup: %s", exc)
    yield
    logger.info("Shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="PayPilot AgentOS",
        description="Hackathon scaffold — PayPal AgentOS + PayGuard AI",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount all routers under /api/v1
    PREFIX = "/api/v1"
    app.include_router(goals.router, prefix=PREFIX)
    app.include_router(plans.router, prefix=PREFIX)
    app.include_router(payments.router, prefix=PREFIX)
    app.include_router(providers.router, prefix=PREFIX)

    # Uniform error handler for HTTPExceptions that have our error envelope
    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": str(exc), "details": None}},
        )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
