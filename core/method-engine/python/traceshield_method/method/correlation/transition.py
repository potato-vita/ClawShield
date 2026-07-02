from typing import Dict, List

from traceshield_method.method.schemas import IntentFrame, SemanticEvent, Violation
from traceshield_method.method.state import TraceState


def check_step_transition(
    intent: IntentFrame,
    state: TraceState,
    event: SemanticEvent,
    transition_rules: Dict[str, List[str]],
) -> List[Violation]:
    previous_action = state.previous_action or "start"
    allowed_next = transition_rules.get(previous_action, [])
    action = event.semantic_action
    is_illegal_transition = action not in allowed_next
    is_high_risk = event.risk_level == "high" or action in intent.forbidden_actions
    if previous_action != "start" and is_illegal_transition and is_high_risk:
        return [
            Violation(
                violation_type="step_step_inconsistency",
                evidence_steps=[state.current_step, event.step_id],
                target=event.target_resource,
                source="step_transition",
                reason=f"执行链从 {previous_action} 跳转到 {action}，缺少与用户意图相关的合理中间步骤。",
            )
        ]
    return []
