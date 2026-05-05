"""Policy actions for minimal semantic guardrails decisions."""


def evaluate_candidate_action(task_type: str, tool_id: str, dialog_state: str) -> dict:
    """Return a deterministic allow/warn/deny semantic decision.

    This decision is intentionally heuristic in Round 3 and does not include
    gateway execution or policy engine evaluation.
    """
    normalized_task = (task_type or "unknown").lower()
    normalized_tool = (tool_id or "").lower()

    if dialog_state == "blocked":
        return {
            "semantic_decision": "deny",
            "semantic_reason": "current dialog state is blocked",
        }

    if normalized_task == "analysis" and "delete" in normalized_tool:
        return {
            "semantic_decision": "deny",
            "semantic_reason": "analysis tasks should not request destructive tools",
        }

    if normalized_task == "analysis" and ("http" in normalized_tool or "plugin" in normalized_tool):
        return {
            "semantic_decision": "warn",
            "semantic_reason": "analysis tasks with outbound or plugin calls require caution",
        }

    return {
        "semantic_decision": "allow",
        "semantic_reason": "candidate tool call matches current semantic context",
    }
