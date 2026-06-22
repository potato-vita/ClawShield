from dataclasses import dataclass
from typing import Any

from app.schemas.plugin import AuditToolCallRequest


@dataclass(frozen=True)
class ToolBoundary:
    source: str
    parameter_node: str
    tool_node: str
    sink: str


class ToolMapper:
    def map(self, request: AuditToolCallRequest) -> ToolBoundary:
        params: dict[str, Any] = request.raw_params or request.params
        text = str(params).lower()
        if request.tool_kind == "network_request" or "http" in text:
            return ToolBoundary("user_goal", "url_param", "network_tool", "external_sink")
        if "rm -rf" in text:
            return ToolBoundary("user_goal", "command_param", "exec_tool", "destructive_action")
        if any(marker in text for marker in (".env", "id_rsa")):
            return ToolBoundary("user_goal", "command_param", "exec_tool", "sensitive_file")
        return ToolBoundary("user_goal", "tool_param", request.tool_kind, "local_resource")
