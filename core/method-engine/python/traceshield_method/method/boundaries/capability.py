from typing import List

from traceshield_method.method.schemas import IntentFrame, SemanticEvent, Violation


def check_capability_boundary(intent: IntentFrame, event: SemanticEvent) -> List[Violation]:
    action = event.semantic_action
    if action in intent.forbidden_actions or (action not in intent.allowed_actions and event.risk_level == "high"):
        return [
            Violation(
                violation_type="intent_tool_inconsistency",
                evidence_steps=[event.step_id],
                target=event.target_resource,
                source="capability_boundary",
                reason=f"工具动作 {action} 不属于当前用户意图允许范围。",
            )
        ]
    return []
