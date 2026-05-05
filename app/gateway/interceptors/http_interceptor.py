from __future__ import annotations

from app.gateway.interceptors.base import BaseInterceptor, InterceptedAction
from app.schemas.tool_call import ActionRequest


class HttpInterceptor(BaseInterceptor):
    def intercept(self, request: ActionRequest) -> InterceptedAction:
        url = str(
            request.arguments.get("url")
            or request.arguments.get("target_url")
            or request.arguments.get("uri")
            or request.arguments.get("endpoint")
            or "unknown_url"
        )
        return InterceptedAction(
            request=request,
            resource_type="http",
            resource_id=url,
        )
