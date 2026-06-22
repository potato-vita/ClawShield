import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditDecision, RiskEvidence, RiskGraphEdge, SecurityEvent, ToolCall


def get_event_detail(db: Session, event_id: str) -> dict | None:
    event = db.get(SecurityEvent, event_id)
    if event is None:
        return None
    call = db.get(ToolCall, event.tool_call_id) if event.tool_call_id else None
    decision = db.get(AuditDecision, event.audit_decision_id) if event.audit_decision_id else None
    evidence = db.scalars(select(RiskEvidence).where(RiskEvidence.tool_call_id == event.tool_call_id)).all()
    edges = db.scalars(select(RiskGraphEdge).where(RiskGraphEdge.tool_call_id == event.tool_call_id)).all()
    return {
        "success": True,
        "event": {
            "event_id": event.id, "risk_level": event.risk_level, "risk_score": event.risk_score,
            "event_status": event.event_status, "timestamp": event.occurred_at.isoformat(),
            "username": event.username, "user_id": event.user_id, "department_name": event.department_name,
            "department_id": event.department_id, "host_name": event.host_name, "host_id": event.host_id,
            "ip_address": event.ip_address, "file_name": event.file_name, "file_path": event.file_path,
            "sensitive_type": event.sensitive_type, "sensitive_level": event.sensitive_level,
            "operation": event.operation, "process_name": event.process_name, "target": event.target,
            "target_type": event.target_type, "event_title": event.event_title,
        },
        "risk_explanation": event.risk_explanation or "检测到潜在风险工具调用。",
        "recommended_actions": json.loads(event.recommended_actions_json or "[]"),
        "tool_call": {} if call is None else {
            "id": call.id, "tool_name": call.tool_name, "tool_kind": call.tool_kind,
            "status": call.status, "decision": call.decision, "resource_value": call.resource_value,
        },
        "audit_decision": {} if decision is None else {
            "id": decision.id, "decision": decision.decision, "risk_level": decision.risk_level,
            "risk_score": decision.risk_score, "reason": decision.reason,
            "matched_rules": json.loads(decision.matched_rules_json or "[]"),
        },
        "evidence": [
            {"id": item.id, "type": item.evidence_type, "key": item.evidence_key,
             "value": item.evidence_value, "description": item.description}
            for item in evidence
        ],
        "risk_graph": [
            {"id": edge.id, "source": edge.source_node, "target": edge.target_node,
             "edge_type": edge.edge_type, "confidence": edge.confidence}
            for edge in edges
        ],
    }
