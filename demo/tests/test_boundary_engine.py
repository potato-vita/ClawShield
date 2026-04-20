from app.core.boundary_engine import BoundaryEngine


def test_workspace_escape_blocked(gateway_context: dict):
    engine: BoundaryEngine = gateway_context["boundary"]
    decision = engine.check_file_access("/etc/passwd", "read")
    assert decision.decision == "block"
    assert decision.rule_id == "R1"


def test_sensitive_file_alert(gateway_context: dict):
    engine: BoundaryEngine = gateway_context["boundary"]
    decision = engine.check_file_access(".env", "read")
    assert decision.decision == "alert"
    assert decision.rule_id == "R2"


def test_allowed_tool(gateway_context: dict):
    engine: BoundaryEngine = gateway_context["boundary"]
    decision = engine.check_tool_invocation("summarize_tool")
    assert decision.decision == "allow"
