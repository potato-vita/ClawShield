from app.schemas.plugin import AuditToolCallRequest
from app.services.audit_engine import AuditEngine
from app.services.risk_graph_builder import RiskGraphBuilder


def request(kind: str, params: dict) -> AuditToolCallRequest:
    return AuditToolCallRequest(
        session_id="s", run_id="r", trace_id="t", tool_call_id="c",
        tool_name="exec", tool_kind=kind, raw_params=params,
    )


def test_boundary_model_detects_sensitive_source_to_sink(db) -> None:
    item = request("shell_exec", {"cmd": "cat .env"})
    result = AuditEngine().audit_tool_call(db, item)
    assert any(evidence.type == "sensitive_path" for evidence in result.evidence)
    assert RiskGraphBuilder().nodes(item) == ["user_goal", "command_param", "exec_tool", "sensitive_file"]


def test_boundary_model_detects_external_and_dangerous_sinks(db) -> None:
    external = request("network_request", {"url": "https://external-upload.com/drop"})
    dangerous = request("shell_exec", {"cmd": "rm -rf /tmp/x"})
    assert any(item.type == "external_sink" for item in AuditEngine().audit_tool_call(db, external).evidence)
    assert RiskGraphBuilder().nodes(dangerous)[-1] == "destructive_action"
