"""FastAPI application entrypoint, lifespan, CORS, error envelope handlers and router mounting."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import db as db_module
from app.config import settings
from app.enums import ErrorCode
from app.errors import ApiError
from app.routers import goals, payments, plans, providers


def _error_response(code: ErrorCode, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code.value, "message": message}},
    )


def create_app(init_db: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        from app.llm import active_provider

        logging.getLogger("uvicorn.error").info(
            "AgentOS: LLM=%s PAYPAL_MODE=%s", active_provider(), settings.PAYPAL_MODE
        )
        if init_db:
            db_module.init_engine()
            try:
                from seed import seed

                with db_module.SessionLocal() as session:
                    seed(session)
            except ImportError:
                pass
        yield

    application = FastAPI(
        title="PayPal AgentOS + PayGuard AI",
        version="1.0.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(ApiError)
    async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
        return _error_response(exc.code, exc.message, exc.status_code)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errs = exc.errors()
        if errs:
            first = errs[0]
            loc = ".".join(str(x) for x in first.get("loc", []))
            msg = f"{loc}: {first.get('msg', 'Invalid input')}" if loc else str(first.get("msg", "Invalid input"))
        else:
            msg = "Validation error"
        return _error_response(ErrorCode.VALIDATION_ERROR, msg, 422)

    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            code = ErrorCode.NOT_FOUND
        elif exc.status_code == 409:
            code = ErrorCode.CONFLICT
        elif exc.status_code == 422:
            code = ErrorCode.VALIDATION_ERROR
        elif exc.status_code == 502:
            code = ErrorCode.PAYPAL_ERROR
        elif exc.status_code == 503:
            code = ErrorCode.PAYMENTS_DISABLED
        elif exc.status_code >= 500:
            code = ErrorCode.INTERNAL_ERROR
        else:
            code = ErrorCode.VALIDATION_ERROR
        message = str(exc.detail) if exc.detail else "HTTP error"
        return _error_response(code, message, exc.status_code)

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
        return _error_response(ErrorCode.INTERNAL_ERROR, "Internal server error", 500)

    prefix = "/api/v1"
    application.include_router(goals.router, prefix=prefix)
    application.include_router(plans.router, prefix=prefix)
    application.include_router(payments.router, prefix=prefix)
    application.include_router(providers.router, prefix=prefix)

    return application


app = create_app()
