from app.adapters.mock_openclaw import MockOpenClawAdapter
from app.models.gateway_models import ExecutionContext


def test_normal_scenario_runs(gateway_context: dict):
    adapter = MockOpenClawAdapter(gateway=gateway_context["gateway"])
    results = adapter.run_normal_task("run_demo_normal")
    assert len(results) == 3
    assert all(r["status"] in {"allowed", "alerted"} for r in results)


def test_workspace_escape_scenario_blocked(gateway_context: dict):
    adapter = MockOpenClawAdapter(gateway=gateway_context["gateway"])
    results = adapter.run_workspace_escape_task("run_demo_escape")
    assert len(results) == 1
    assert results[0]["status"] == "blocked"


def test_sensitive_exfiltration_scenario_detects_block(gateway_context: dict):
    adapter = MockOpenClawAdapter(gateway=gateway_context["gateway"])
    results = adapter.run_sensitive_exfiltration_task("run_demo_exfil")
    assert len(results) == 2
    assert results[1]["decision"] == "block"


def test_advanced_intrusion_kill_chain_has_multiple_blocks(gateway_context: dict):
    adapter = MockOpenClawAdapter(gateway=gateway_context["gateway"])
    results = adapter.run_advanced_intrusion_kill_chain("run_demo_advanced")

    assert len(results) >= 10
    blocked_count = len([r for r in results if r["status"] == "blocked"])
    assert blocked_count >= 4
