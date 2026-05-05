from __future__ import annotations

from app.gateway.interceptors.base import BaseInterceptor, InterceptedAction
from app.schemas.tool_call import ActionRequest


class ToolCallInterceptor(BaseInterceptor):
    def intercept(self, request: ActionRequest) -> InterceptedAction:
        return InterceptedAction(
            request=request,
            resource_type="tool",
            resource_id=request.tool_id,
        )
