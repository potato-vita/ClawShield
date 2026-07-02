from typing import Any, Dict, List, Tuple

from traceshield_method.method import IntentFrame, SemanticEvent, ToolEvent, TraceShieldEvaluator
from traceshield_method.method.profiles import switches_for_profile
from traceshield_method.runtime_schemas import RuntimeEvent, RuntimeParams


TOOL_KIND_FALLBACK = {
    "file_read": ("file", "read_file", "medium"),
    "file_write": ("file", "write_file", "medium"),
    "file_delete": ("file", "delete_file", "high"),
    "shell_exec": ("shell", "shell_exec", "high"),
    "network_request": ("network", "network_post", "high"),
    "message_send": ("network", "send_email", "high"),
    "plugin_install": ("system", "install_plugin", "high"),
}


def build_intent(params: RuntimeParams) -> IntentFrame:
    source = params.intent_frame
    constraints = dict(source.constraints)
    if source.authorized_risky_calls:
        constraints["authorized_risky_calls"] = source.authorized_risky_calls
    return IntentFrame(
        task_goal=source.task_goal,
        allowed_actions=source.allowed_actions,
        allowed_resources=source.allowed_resources,
        forbidden_actions=source.forbidden_actions,
        forbidden_resources=source.forbidden_resources,
        sensitive_resources=source.sensitive_resources,
        constraints=constraints,
    )


def build_tool_events(events: List[RuntimeEvent]) -> List[ToolEvent]:
    return [
        ToolEvent(
            step_id=event.step_id,
            tool_name=event.tool_name,
            args=event.args,
            observation=event.observation,
        )
        for event in sorted(events, key=lambda item: item.step_id)
    ]


def evaluate_runtime(params: RuntimeParams) -> Dict[str, Any]:
    if params.profile != "balanced" or params.profile_version != "balanced-v1":
        raise ValueError(f"Unsupported profile: {params.profile}/{params.profile_version}")
    evaluator = TraceShieldEvaluator(switches=switches_for_profile("strict"))
    intent = build_intent(params)
    tool_events = build_tool_events(params.events)
    semantic_events, mappings = map_events(evaluator, params.events, tool_events)
    result = evaluator.evaluate_tool_events(params.run_id, intent, tool_events, mapper=RuntimeMapper(semantic_events))
    current = [item for item in result.violations if params.current_step_seq in item.evidence_steps]
    return {
        "audit_result": result,
        "semantic_events": semantic_events,
        "mappings": mappings,
        "current_violations": current,
    }


class RuntimeMapper:
    def __init__(self, semantic_events: List[SemanticEvent]):
        self.events = {event.step_id: event for event in semantic_events}

    def map_event(self, event: ToolEvent) -> SemanticEvent:
        return self.events[event.step_id]


def map_events(
    evaluator: TraceShieldEvaluator,
    runtime_events: List[RuntimeEvent],
    tool_events: List[ToolEvent],
) -> Tuple[List[SemanticEvent], List[Dict[str, Any]]]:
    semantic_events: List[SemanticEvent] = []
    mappings: List[Dict[str, Any]] = []
    by_step = {event.step_id: event for event in runtime_events}
    for tool_event in tool_events:
        runtime_event = by_step[tool_event.step_id]
        semantic = evaluator.mapper.map_event(tool_event)
        source = "exact_registry"
        confidence = 1.0
        if semantic.tool_type == "unknown":
            fallback = TOOL_KIND_FALLBACK.get(runtime_event.tool_kind)
            if fallback:
                tool_type, action, risk = fallback
                semantic = SemanticEvent(
                    step_id=tool_event.step_id,
                    tool_name=tool_event.tool_name,
                    tool_type=tool_type,
                    semantic_action=runtime_event.semantic_action_hint or action,
                    target_resource=runtime_event.target_resource_hint,
                    risk_level=risk,
                    raw_event=tool_event,
                )
                source = "tool_kind_fallback"
                confidence = 0.7
            else:
                source = "unknown"
                confidence = 0.0
        elif runtime_event.target_resource_hint and not semantic.target_resource:
            semantic.target_resource = runtime_event.target_resource_hint
        semantic_events.append(semantic)
        mappings.append(
            {
                "step_id": semantic.step_id,
                "registry_version": "v2",
                "mapping_source": source,
                "mapping_confidence": confidence,
            }
        )
    return semantic_events, mappings
