from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class APIError(BaseModel):
    error_code: str
    details: Any | None = None


class APIResponse(BaseModel):
    success: bool = Field(default=True)
    message: str = Field(default="ok")
    data: Any | None = None
    error: APIError | None = None


def success_response(data: Any = None, message: str = "ok") -> APIResponse:
    return APIResponse(success=True, message=message, data=data)


def error_response(message: str, error_code: str, details: Any | None = None) -> APIResponse:
    return APIResponse(
        success=False,
        message=message,
        data=None,
        error=APIError(error_code=error_code, details=details),
    )


def not_implemented_response(message: str = "not implemented yet") -> APIResponse:
    return error_response(message=message, error_code="NOT_IMPLEMENTED")
