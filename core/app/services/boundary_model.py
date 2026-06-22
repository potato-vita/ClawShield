from app.schemas.plugin import AuditToolCallRequest, EvidenceItem


class BoundaryModel:
    def analyze(self, request: AuditToolCallRequest) -> list[EvidenceItem]:
        params = request.raw_params or request.params
        text = str(params).lower()
        if ".env" in text or "id_rsa" in text:
            marker = "id_rsa" if "id_rsa" in text else ".env"
            return [EvidenceItem(type="sensitive_path", key="path", value=marker, description="检测到从工具参数到敏感文件的访问边界")]
        if request.tool_kind == "network_request":
            return [EvidenceItem(type="external_sink", key="url", value=request.resource_hint or str(params.get("url", "")), description="检测到工具参数流向外部网络目标")]
        if "rm -rf" in text:
            return [EvidenceItem(type="dangerous_command", key="cmd", value="rm -rf", description="检测到破坏性命令边界")]
        return []
