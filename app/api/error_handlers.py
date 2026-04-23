from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError
from app.schemas.common import error_response

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_, exc: AppError) -> JSONResponse:
        logger.warning(
            "Handled AppError error_code=%s status=%s message=%s details=%s",
            exc.error_code,
            exc.status_code,
            exc.message,
            exc.details,
        )
        payload = error_response(
            message=exc.message,
            error_code=exc.error_code,
            details=exc.details,
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_, exc: RequestValidationError) -> JSONResponse:
        payload = error_response(
            message="request validation failed",
            error_code="VALIDATION_ERROR",
            details=exc.errors(),
        )
        return JSONResponse(status_code=422, content=payload.model_dump())

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_, exc: StarletteHTTPException) -> JSONResponse:
        payload = error_response(
            message=str(exc.detail),
            error_code="HTTP_ERROR",
            details={"status_code": exc.status_code},
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def handle_unknown_error(_, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API exception", exc_info=exc)
        payload = error_response(
            message="internal server error",
            error_code="INTERNAL_SERVER_ERROR",
            details=str(exc),
        )
        return JSONResponse(status_code=500, content=payload.model_dump())
