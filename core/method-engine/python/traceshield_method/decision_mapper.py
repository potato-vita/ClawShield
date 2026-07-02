from typing import Any, Dict, List

from traceshield_method.method.schemas import SemanticEvent, Violation


HARD_VIOLATIONS = {
    "prompt_injection_induced_drift",
    "chain_semantic_drift",
    "intent_resource_inconsistency",
}


def map_runtime_decision(
    current_step: int,
    semantic_events: List[SemanticEvent],
    current_violations: List[Violation],
    all_violations: List[Violation],
    mappings: List[Dict[str, Any]],
) -> Dict[str, str]:
    event = next((item for item in semantic_events if item.step_id == current_step), None)
    mapping = next((item for item in mappings if item["step_id"] == current_step), {})
    if current_violations:
        hard = any(item.violation_type in HARD_VIOLATIONS for item in current_violations)
        if hard and event and event.risk_level in {"medium", "high", "critical"}:
            return {"runtime_suggestion": "BLOCK", "risk_level": "critical" if event.risk_level == "high" else "high"}
        if event and event.risk_level in {"high", "critical"}:
            return {"runtime_suggestion": "ASK", "risk_level": "high"}
        return {"runtime_suggestion": "WARN", "risk_level": "medium"}
    if mapping.get("mapping_source") == "unknown":
        return {"runtime_suggestion": "ASK", "risk_level": "high"}
    if mapping.get("mapping_confidence", 1.0) < 0.8:
        return {"runtime_suggestion": "WARN", "risk_level": "medium"}
    if all_violations:
        return {"runtime_suggestion": "WARN", "risk_level": "medium"}
    return {"runtime_suggestion": "ALLOW", "risk_level": "low"}

