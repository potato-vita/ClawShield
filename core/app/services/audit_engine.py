from app.schemas.plugin import ApprovalInfo, AuditDecisionResponse, AuditToolCallRequest, EvidenceItem
from app.services.idgen import new_id
from app.services.boundary_model import BoundaryModel
from app.services.rule_engine import RuleEngine


class AuditEngine:
    def __init__(self, rule_engine: RuleEngine | None = None, boundary_model: BoundaryModel | None = None) -> None:
        self.rule_engine = rule_engine or RuleEngine()
        self.boundary_model = boundary_model or BoundaryModel()

    def audit_tool_call(self, db, request: AuditToolCallRequest) -> AuditDecisionResponse:  # type: ignore[no-untyped-def]
        result = self.rule_engine.evaluate(db, request)
        approval = None
        if result.decision == "ASK":
            approval = ApprovalInfo(
                approval_id=new_id("approval"),
                title=result.event_title,
                description=result.reason,
                default_action="BLOCK",
                timeout_ms=30_000,
            )
        evidence = [EvidenceItem.model_validate(item) for item in result.evidence]
        for item in self.boundary_model.analyze(request):
            if not any(existing.type == item.type and existing.value == item.value for existing in evidence):
                evidence.append(item)
        return AuditDecisionResponse(
            decision=result.decision,
            risk_level=result.risk_level,
            risk_score=result.risk_score,
            reason=result.reason,
            matched_rules=result.matched_rules,
            approval=approval,
            evidence=evidence,
        )
