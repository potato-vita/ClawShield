from traceshield_method.runtime_adapter import evaluate_runtime
from traceshield_method.runtime_schemas import RuntimeParams


def params(events: list[dict], current: int) -> RuntimeParams:
    return RuntimeParams.model_validate(
        {
            "session_id": "s",
            "run_id": "r",
            "trace_id": "t",
            "current_step_seq": current,
            "profile": "balanced",
            "profile_version": "balanced-v1",
            "intent_frame": {
                "task_goal": "read a public file only",
                "allowed_actions": ["read_file", "final_answer"],
                "allowed_resources": ["README.md"],
                "sensitive_resources": [".env"],
            },
            "events": events,
        }
    )


def test_runtime_adapter_uses_tool_kind_fallback() -> None:
    result = evaluate_runtime(
        params(
            [{"step_id": 1, "tool_name": "custom_reader", "tool_kind": "file_read", "args": {"path": "README.md"}}],
            1,
        )
    )
    assert result["mappings"][0]["mapping_source"] == "tool_kind_fallback"
    assert result["semantic_events"][0].semantic_action == "read_file"


def test_current_violations_do_not_include_history_only_violation() -> None:
    result = evaluate_runtime(
        params(
            [
                {"step_id": 1, "tool_name": "read_file", "tool_kind": "file_read", "args": {"path": ".env"}},
                {"step_id": 2, "tool_name": "read_file", "tool_kind": "file_read", "args": {"path": "README.md"}},
            ],
            2,
        )
    )
    assert result["audit_result"].violations
    assert result["current_violations"] == []

