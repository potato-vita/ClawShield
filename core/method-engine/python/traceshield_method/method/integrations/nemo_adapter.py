from typing import Any, Dict, Optional

from traceshield_method.method.evaluator import TraceShieldEvaluator
from traceshield_method.method.schemas import IntentFrame, ToolEvent


def evaluate_nemo_tool_call(
    tool_name: str,
    args: Optional[Dict[str, Any]],
    intent_frame: Dict[str, Any],
    step_id: int = 1,
    observation: Optional[str] = None,
    evaluator: Optional[TraceShieldEvaluator] = None,
) -> Dict[str, Any]:
    """Evaluate one NeMo execution-rail tool call with TraceShield.

    This adapter is intentionally dependency-light. A NeMo `actions.py` file can
    call it from a custom action, while the core package remains usable without
    installing `nemoguardrails`.
    """

    active_evaluator = evaluator or TraceShieldEvaluator()
    intent = IntentFrame.model_validate(intent_frame)
    event = ToolEvent(
        step_id=step_id,
        tool_name=tool_name,
        args=args or {},
        observation=observation,
    )
    result = active_evaluator.evaluate_tool_events("nemo_tool_call", intent, [event])
    return {
        "allowed": result.decision == "allow",
        "decision": result.decision,
        "primary_violation_type": result.primary_violation_type,
        "evidence_steps": result.evidence_steps,
        "explanation": result.explanation,
        "violations": [violation.model_dump() for violation in result.violations],
    }


def build_nemo_tool_action(evaluator: Optional[TraceShieldEvaluator] = None):
    active_evaluator = evaluator or TraceShieldEvaluator()

    async def traceshield_check_tool_call(
        tool_name: str,
        args: Optional[Dict[str, Any]] = None,
        intent_frame: Optional[Dict[str, Any]] = None,
        step_id: int = 1,
        observation: Optional[str] = None,
    ) -> Dict[str, Any]:
        return evaluate_nemo_tool_call(
            tool_name=tool_name,
            args=args or {},
            intent_frame=intent_frame or {"task_goal": "unknown"},
            step_id=step_id,
            observation=observation,
            evaluator=active_evaluator,
        )

    return traceshield_check_tool_call
