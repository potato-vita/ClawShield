import json
import time
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import Approval, AuditDecision, RiskEvidence, RiskGraphEdge, SecurityEvent, ToolCall
from app.db.repositories import get_or_create_run
from app.db.session import get_db
from app.schemas.plugin import AuditDecisionResponse, AuditToolCallRequest
from app.services.audit_engine import AuditEngine
from app.services.idgen import new_id
from app.services.sanitizer import json_text, redact_text, stable_hash
from app.services.timeutil import parse_timestamp
from app.services.risk_graph_builder import RiskGraphBuilder

router = APIRouter(tags=["plugin"])
engine = AuditEngine()
graph_builder = RiskGraphBuilder()


@router.post("/v1/audit/tool-call", response_model=AuditDecisionResponse)
def audit_tool_call(request: AuditToolCallRequest, db: Session = Depends(get_db)) -> AuditDecisionResponse:
    started = time.perf_counter()
    run = get_or_create_run(db, request.run_id, request.session_id, request.context.user_goal)
    call = db.get(ToolCall, request.tool_call_id)
    is_new = call is None
    params = request.raw_params or request.params
    if call is None:
        call = ToolCall(
            id=request.tool_call_id,
            run_id=request.run_id,
            session_id=request.session_id,
            trace_id=request.trace_id,
            tool_name=request.tool_name,
            tool_kind=request.tool_kind,
            status="audited",
            raw_params_json=json_text(params),
            sanitized_params_json=json_text(params),
            param_summary=json_text(request.param_summary),
            resource_value=redact_text(request.resource_hint or "", 300),
            started_at=parse_timestamp(request.timestamp),
        )
        db.add(call)
        db.flush()

    response = engine.audit_tool_call(db, request)
    call.decision = response.decision
    call.status = "blocked" if response.decision == "BLOCK" else "awaiting_approval" if response.decision == "ASK" else "audited"
    decision_id = new_id("decision")
    decision = AuditDecision(
        id=decision_id,
        tool_call_id=call.id,
        decision=response.decision,
        risk_level=response.risk_level,
        risk_score=response.risk_score,
        reason=response.reason,
        matched_rules_json=json.dumps(response.matched_rules, ensure_ascii=False),
        modified_params_json=json_text(response.modified_params) if response.modified_params else None,
        fallback_used=response.fallback_used,
        core_latency_ms=int((time.perf_counter() - started) * 1000),
    )
    db.add(decision)
    db.flush()

    if is_new:
        run.total_tool_calls += 1
    if response.decision == "BLOCK":
        run.blocked_count += 1
    elif response.decision == "ASK":
        run.ask_count += 1
    elif response.decision == "WARN":
        run.warn_count += 1

    evidence_ids: list[str] = []
    for item in response.evidence:
        evidence_id = new_id("evidence")
        evidence_ids.append(evidence_id)
        db.add(RiskEvidence(
            id=evidence_id,
            audit_decision_id=decision_id,
            tool_call_id=call.id,
            evidence_type=item.type,
            evidence_key=item.key,
            evidence_value=redact_text(item.value or "", 300),
            evidence_hash=stable_hash(item.value or ""),
            description=item.description,
        ))

    if response.decision != "ALLOW":
        event_id = new_id("event")
        resource = request.resource_hint or next((str(params.get(key)) for key in ("path", "url", "cmd") if params.get(key)), "")
        is_network = request.tool_kind == "network_request" or resource.startswith(("http://", "https://"))
        file_path = resource if not is_network and ("/" in resource or ".env" in resource or "id_rsa" in resource) else None
        security = SecurityEvent(
            id=event_id,
            session_id=request.session_id,
            run_id=request.run_id,
            tool_call_id=call.id,
            audit_decision_id=decision_id,
            event_title=_event_title(response.matched_rules, resource),
            event_type=_event_type(response.matched_rules),
            risk_level=response.risk_level,
            risk_score=response.risk_score,
            username=request.context.username,
            department_name=request.context.department_name,
            host_name=request.context.host_name,
            ip_address=request.context.ip_address,
            file_name=Path(file_path).name if file_path else None,
            file_path=redact_text(file_path, 300) if file_path else None,
            sensitive_type="credential" if any(x in resource.lower() for x in (".env", "id_rsa")) else None,
            sensitive_level="S4" if response.risk_level == "critical" else "S3",
            operation=request.tool_kind,
            process_name="openclaw",
            target=redact_text(resource, 300),
            target_type="network" if is_network else "file" if file_path else "operation",
            risk_explanation=response.reason,
            recommended_actions_json=json.dumps(["保持当前处置结果", "复核用户任务目标", "检查相关策略与凭据暴露范围"], ensure_ascii=False),
            occurred_at=parse_timestamp(request.timestamp),
        )
        db.add(security)

        nodes = graph_builder.nodes(request)
        for index in range(len(nodes) - 1):
            db.add(RiskGraphEdge(
                id=new_id("edge"),
                run_id=request.run_id,
                tool_call_id=call.id,
                source_node=nodes[index],
                target_node=nodes[index + 1],
                edge_type="flows_to",
                evidence_id=evidence_ids[0] if evidence_ids else None,
            ))

    if response.approval:
        db.add(Approval(
            id=response.approval.approval_id,
            tool_call_id=call.id,
            audit_decision_id=decision_id,
            session_id=request.session_id,
            status="pending",
        ))

    db.commit()
    return response


def _event_type(rules: list[str]) -> str:
    rule = " ".join(rules)
    if "rm" in rule or "dangerous" in rule:
        return "dangerous_command"
    if "external" in rule or "network" in rule:
        return "external_upload"
    if "secret" in rule or "private" in rule:
        return "sensitive_file_access"
    return "policy_violation"


def _event_title(rules: list[str], resource: str) -> str:
    kind = _event_type(rules)
    return {
        "dangerous_command": "阻止危险命令",
        "external_upload": "外部网络操作需要审批",
        "sensitive_file_access": f"阻止读取敏感文件 {Path(resource).name}",
    }.get(kind, "检测到风险工具调用")
