from app.schemas.plugin import AuditToolCallRequest
from app.services.tool_mapper import ToolMapper


class RiskGraphBuilder:
    def __init__(self, mapper: ToolMapper | None = None) -> None:
        self.mapper = mapper or ToolMapper()

    def nodes(self, request: AuditToolCallRequest) -> list[str]:
        boundary = self.mapper.map(request)
        return [boundary.source, boundary.parameter_node, boundary.tool_node, boundary.sink]
