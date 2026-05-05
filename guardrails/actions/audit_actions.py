"""Audit action helpers for semantic guardrail events."""


def build_semantic_events(run_id: str, task_type: str, dialog_state: str, decision: str, reason: str) -> list[dict]:
    """Build minimal semantic event payloads for persistence.

    Persistence is intentionally handled by app/services/guardrails_service.py.
    """
    return [
        {
            "run_id": run_id,
            "event_type": "task_classified",
            "event_stage": "semantic_guard",
            "semantic_decision": None,
            "input_summary": f"task_type={task_type}",
        },
        {
            "run_id": run_id,
            "event_type": "dialog_state_changed",
            "event_stage": "semantic_guard",
            "semantic_decision": None,
            "input_summary": f"dialog_state={dialog_state}",
        },
        {
            "run_id": run_id,
            "event_type": "semantic_check_completed",
            "event_stage": "semantic_guard",
            "semantic_decision": decision,
            "input_summary": reason,
        },
    ]
