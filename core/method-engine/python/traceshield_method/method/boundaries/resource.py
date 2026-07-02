from typing import List, Optional

from traceshield_method.method.schemas import IntentFrame, SemanticEvent, Violation
from traceshield_method.method.state import TraceState


def check_resource_boundary(intent: IntentFrame, event: SemanticEvent) -> List[Violation]:
    target = event.target_resource
    if not target:
        return []
    targets = target_resources(target)
    forbidden_target = first_matching_resource(targets, intent.forbidden_resources)
    if forbidden_target:
        return [
            Violation(
                violation_type="intent_resource_inconsistency",
                evidence_steps=[event.step_id],
                target=forbidden_target,
                source="resource_boundary",
                reason=f"资源 {forbidden_target} 属于当前任务明确禁止访问的资源。",
            )
        ]
    if intent.allowed_resources and not any(resource_matches(candidate, pattern) for candidate in targets for pattern in intent.allowed_resources):
        if any(TraceState.is_sensitive_resource(candidate, intent) for candidate in targets) or event.risk_level == "high":
            return [
                Violation(
                    violation_type="intent_resource_inconsistency",
                    evidence_steps=[event.step_id],
                    target=target,
                    source="resource_boundary",
                    reason=f"资源 {target} 不属于当前任务允许访问范围。",
                )
            ]
    return []


def target_resources(target: str) -> List[str]:
    return [resource.strip() for resource in target.split(";") if resource.strip()]


def first_matching_resource(resources: List[str], patterns: List[str]) -> Optional[str]:
    for resource in resources:
        if any(resource_matches(resource, pattern) for pattern in patterns):
            return resource
    return None


def resource_matches(resource: str, pattern: str) -> bool:
    normalized_resource = resource.replace("\\", "/").strip()
    normalized_pattern = pattern.replace("\\", "/").strip()
    if normalized_pattern.endswith("/**"):
        prefix = normalized_pattern[:-3]
        return normalized_resource == prefix or normalized_resource.startswith(prefix + "/")
    if normalized_pattern.startswith("*"):
        return normalized_resource.endswith(normalized_pattern[1:])
    return normalized_resource == normalized_pattern
