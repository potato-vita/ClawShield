from __future__ import annotations

from dataclasses import dataclass

from app.schemas.tool_call import ActionRequest


@dataclass
class InterceptedAction:
    request: ActionRequest
    resource_type: str
    resource_id: str


class BaseInterceptor:
    """Extract resource identity for a normalized action request."""

    def intercept(self, request: ActionRequest) -> InterceptedAction:
        raise NotImplementedError
