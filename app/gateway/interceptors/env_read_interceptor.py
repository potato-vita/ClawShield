from __future__ import annotations

from app.gateway.interceptors.base import BaseInterceptor, InterceptedAction
from app.schemas.tool_call import ActionRequest


class EnvReadInterceptor(BaseInterceptor):
    def intercept(self, request: ActionRequest) -> InterceptedAction:
        key = str(
            request.arguments.get("env_key")
            or request.arguments.get("env_var")
            or request.arguments.get("env_name")
            or request.arguments.get("name")
            or "unknown_env_key"
        )
        return InterceptedAction(
            request=request,
            resource_type="env",
            resource_id=key,
        )
