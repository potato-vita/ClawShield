from __future__ import annotations

from typing import Any


def normalize_event(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "run_id": payload.get("run_id"),
        "session_id": payload.get("session_id"),
        "event_type": payload.get("event_type"),
        "event_stage": payload.get("event_stage"),
        "actor_type": payload.get("actor_type"),
        "actor_id": payload.get("actor_id"),
        "tool_id": payload.get("tool_id"),
        "resource_type": payload.get("resource_type"),
        "resource_id": payload.get("resource_id"),
        "input_summary": payload.get("input_summary"),
        "output_summary": payload.get("output_summary"),
        "semantic_decision": payload.get("semantic_decision"),
        "policy_decision": payload.get("policy_decision"),
        "risk_level": payload.get("risk_level"),
        "disposition": payload.get("disposition"),
        "status": payload.get("status"),
        "tool_call_id": payload.get("tool_call_id"),
        "step_id": payload.get("step_id"),
        "parent_event_id": payload.get("parent_event_id"),
        "span_id": payload.get("span_id"),
        "metadata_json": payload.get("metadata_json"),
        "alignment_score": payload.get("alignment_score"),
        "alignment_decision": payload.get("alignment_decision"),
        "alignment_reason": payload.get("alignment_reason"),
        "intended_effect": payload.get("intended_effect"),
        "actual_effect": payload.get("actual_effect"),
        "impact_level": payload.get("impact_level"),
        "argument_digest": payload.get("argument_digest"),
    }

    # Default values keep event shape stable across producers.
    normalized["event_stage"] = normalized["event_stage"] or "ingest"
    normalized["actor_type"] = normalized["actor_type"] or "system"
    normalized["status"] = normalized["status"] or "recorded"
    return normalized
