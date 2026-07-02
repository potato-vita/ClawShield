from typing import List, Optional

from traceshield_method.method.schemas import AuditResult, Violation, select_primary_violation


ALLOW_EXPLANATION = "未发现工具调用与用户意图、资源范围或执行链状态之间的不一致。"


def build_audit_result(
    sample_id: str,
    violations: List[Violation],
    latency_ms: Optional[float] = None,
) -> AuditResult:
    evidence_steps = sorted({step for violation in violations for step in violation.evidence_steps})
    primary_violation = select_primary_violation(violations)
    decision = "deny" if violations else "allow"
    return AuditResult(
        sample_id=sample_id,
        decision=decision,
        violations=violations,
        evidence_steps=evidence_steps,
        primary_violation_type=primary_violation.violation_type if primary_violation else None,
        primary_evidence_steps=primary_violation.evidence_steps if primary_violation else [],
        explanation=build_explanation(violations),
        latency_ms=latency_ms,
    )


def build_explanation(violations: List[Violation]) -> str:
    if not violations:
        return ALLOW_EXPLANATION
    if len(violations) == 1:
        return violations[0].reason
    ordered = sorted(violations, key=lambda item: min(item.evidence_steps or [10**9]))
    return "；".join(violation.reason for violation in ordered) + "；因此判定为 deny。"
