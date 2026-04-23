"""Task context actions for minimal guardrails workflow."""


def get_task_context(run_id: str, task_type: str, run_status: str) -> dict:
    """Normalize run context into guardrails-facing state fields.

    The function is pure on purpose: I/O stays in the service layer.
    """
    status_to_state = {
        "created": "task_received",
        "analyzing": "analyzing",
        "tool_pending": "planning_tool_use",
        "blocked": "blocked",
        "finished": "analyzing",
    }
    return {
        "run_id": run_id,
        "task_type": task_type or "unknown",
        "dialog_state": status_to_state.get(run_status, "analyzing"),
    }
