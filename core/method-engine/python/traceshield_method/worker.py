import json
import sys
from typing import Any, Dict

from pydantic import ValidationError

from traceshield_method.decision_mapper import map_runtime_decision
from traceshield_method.runtime_adapter import evaluate_runtime
from traceshield_method.runtime_schemas import RuntimeRequest, RuntimeResponse
from traceshield_method.runtime_schemas import RuntimeParams
from traceshield_method.method.detectors import contains_prompt_injection


def health_result() -> Dict[str, Any]:
    return {
        "status": "ok",
        "protocol_version": "v1",
        "method_version": "phase0-baseline",
        "profiles": ["balanced-v1"],
        "registry_version": "v2",
    }


def handle_request(request: RuntimeRequest) -> RuntimeResponse:
    if request.method == "health":
        return RuntimeResponse(request_id=request.request_id, ok=True, result=health_result())
    if request.method == "shutdown":
        return RuntimeResponse(request_id=request.request_id, ok=True, result={"status": "shutting_down"})
    if request.params is None:
        return error_response(request.request_id, "invalid_request", "params are required")
    if request.method == "detect_observation":
        observation = request.params.get("observation")
        text = observation if isinstance(observation, str) else json.dumps(observation, ensure_ascii=False)
        detected = contains_prompt_injection(text)
        return RuntimeResponse(
            request_id=request.request_id,
            ok=True,
            result={
                "injection_detected": detected,
                "injection_score": 1.0 if detected else 0.0,
                "injection_reasons": ["prompt_injection_pattern"] if detected else [],
            },
        )
    params = RuntimeParams.model_validate(request.params)
    evaluated = evaluate_runtime(params)
    audit_result = evaluated["audit_result"]
    semantic_events = evaluated["semantic_events"]
    mappings = evaluated["mappings"]
    current = evaluated["current_violations"]
    decision = map_runtime_decision(
        params.current_step_seq,
        semantic_events,
        current,
        audit_result.violations,
        mappings,
    )
    graph = project_graph(semantic_events, audit_result.violations)
    mapping = next(
        (item for item in mappings if item["step_id"] == params.current_step_seq),
        {"registry_version": "v2", "mapping_source": "unknown", "mapping_confidence": 0.0},
    )
    result = {
        "method_decision": audit_result.decision,
        **decision,
        "current_step_violations": [item.model_dump(mode="json") for item in current],
        "all_violations": [item.model_dump(mode="json") for item in audit_result.violations],
        "semantic_events": [item.model_dump(mode="json") for item in semantic_events],
        "risk_paths": [item.evidence_steps for item in audit_result.violations],
        "graph_projection": graph,
        "mapping": mapping,
        "latency_ms": audit_result.latency_ms,
    }
    return RuntimeResponse(request_id=request.request_id, ok=True, result=result)


def project_graph(events: list[Any], violations: list[Any]) -> Dict[str, Any]:
    nodes = [{"id": "intent", "type": "user_intent", "label": "User Intent"}]
    edges = []
    previous = "intent"
    for event in events:
        node_id = f"step:{event.step_id}"
        nodes.append({
            "id": node_id,
            "type": "tool_call",
            "label": event.tool_name,
            "step_seq": event.step_id,
            "semantic_action": event.semantic_action,
            "target_resource": event.target_resource,
            "risk_level": event.risk_level,
        })
        edges.append({"id": f"flow:{previous}:{node_id}", "source": previous, "target": node_id, "type": "flow"})
        previous = node_id
    for index, violation in enumerate(violations):
        violation_id = f"violation:{index}"
        nodes.append({"id": violation_id, "type": "policy_violation", "label": violation.violation_type})
        for step in violation.evidence_steps:
            edges.append({"id": f"blocked:{step}:{index}", "source": f"step:{step}", "target": violation_id, "type": "blocked_by"})
    return {"nodes": nodes, "edges": edges}


def error_response(request_id: str, code: str, message: str) -> RuntimeResponse:
    return RuntimeResponse(request_id=request_id, ok=False, error={"code": code, "message": message})


def process_line(line: str) -> RuntimeResponse:
    request_id = "unknown"
    try:
        payload = json.loads(line)
        if isinstance(payload, dict) and isinstance(payload.get("request_id"), str):
            request_id = payload["request_id"]
        return handle_request(RuntimeRequest.model_validate(payload))
    except (json.JSONDecodeError, ValidationError) as error:
        return error_response(request_id, "invalid_request", str(error))
    except Exception as error:
        print(f"worker request failed: {error}", file=sys.stderr, flush=True)
        return error_response(request_id, "evaluation_error", str(error))


def main() -> None:
    for line in sys.stdin:
        response = process_line(line)
        print(response.model_dump_json(exclude_none=True), flush=True)
        if response.ok and response.result and response.result.get("status") == "shutting_down":
            break


if __name__ == "__main__":
    main()
