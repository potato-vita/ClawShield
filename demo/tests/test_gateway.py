from app.models.gateway_models import ExecutionContext


def test_gateway_read_and_write(gateway_context: dict):
    gateway = gateway_context["gateway"]
    ctx = ExecutionContext(run_id="run_test_1", task_id="task_1", skill_id="skill_a")

    read_res = gateway.read_file(ctx, "docs/brief.txt")
    assert read_res.status in {"allowed", "alerted"}
    assert "content" in read_res.result

    write_res = gateway.write_file(ctx, "output/result.txt", "ok")
    assert write_res.status in {"allowed", "alerted"}
    assert write_res.result["written"] is True


def test_gateway_blocks_workspace_escape(gateway_context: dict):
    gateway = gateway_context["gateway"]
    ctx = ExecutionContext(run_id="run_test_2", task_id="task_2", skill_id="skill_probe")

    blocked = gateway.read_file(ctx, "/etc/passwd")
    assert blocked.status == "blocked"
    assert blocked.decision == "block"
