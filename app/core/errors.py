from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base typed application error with API-contract metadata."""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    def __init__(
        self,
        message: str,
        details: Any | None = None,
        error_code: str = "NOT_FOUND",
    ) -> None:
        super().__init__(message=message, error_code=error_code, status_code=404, details=details)


class BadRequestError(AppError):
    def __init__(
        self,
        message: str,
        details: Any | None = None,
        error_code: str = "BAD_REQUEST",
    ) -> None:
        super().__init__(message=message, error_code=error_code, status_code=400, details=details)


class ConfigError(AppError):
    def __init__(self, message: str, details: Any | None = None) -> None:
        super().__init__(message=message, error_code="CONFIG_ERROR", status_code=500, details=details)


class RuntimePipelineError(AppError):
    def __init__(
        self,
        message: str,
        details: Any | None = None,
        error_code: str = "PIPELINE_ERROR",
        status_code: int = 500,
    ) -> None:
        super().__init__(message=message, error_code=error_code, status_code=status_code, details=details)
