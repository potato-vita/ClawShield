from __future__ import annotations

from app.gateway.interceptors.base import BaseInterceptor, InterceptedAction
from app.schemas.tool_call import ActionRequest


class FileReadInterceptor(BaseInterceptor):
    def intercept(self, request: ActionRequest) -> InterceptedAction:
        file_path = str(
            request.arguments.get("file_path")
            or request.arguments.get("path")
            or request.arguments.get("target_file")
            or request.arguments.get("filepath")
            or "unknown_file"
        )
        return InterceptedAction(
            request=request,
            resource_type="file",
            resource_id=file_path,
        )
