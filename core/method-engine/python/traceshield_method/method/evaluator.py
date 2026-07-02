import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from traceshield_method.method.adapters import ToolSemanticMapper
from traceshield_method.method.boundaries import (
    check_capability_boundary,
    check_resource_boundary,
    is_authorized_risky_call,
)
from traceshield_method.method.config import load_yaml, resolve_config_path
from traceshield_method.method.correlation import (
    check_prompt_injection_drift,
    check_sensitive_external_chain,
    check_step_transition,
)
from traceshield_method.method.reporter import build_audit_result
from traceshield_method.method.schemas import AuditResult, DatasetSample, IntentFrame, SemanticEvent, ToolEvent, Violation
from traceshield_method.method.state import TraceState


@dataclass(frozen=True)
class EvaluationSwitches:
    capability_boundary: bool = True
    resource_boundary: bool = True
    authorization_boundary: bool = True
    semantic_relation: bool = True
    step_transition: bool = True
    prompt_injection: bool = True
    sensitive_external_chain: bool = True
    risk_graph_analysis: bool = True
    destructive_after_read: bool = True


class TraceShieldEvaluator:
    def __init__(
        self,
        tool_registry_path: Optional[str | Path] = None,
        transition_rules_path: Optional[str | Path] = None,
        risk_rules_path: Optional[str | Path] = None,
        security_knowledge_path: Optional[str | Path] = None,
        switches: Optional[EvaluationSwitches] = None,
    ):
        self.switches = switches or EvaluationSwitches()
        self.mapper = ToolSemanticMapper(tool_registry_path)
        self.transition_rules = load_yaml(resolve_config_path(transition_rules_path, "transition_rules.yaml")).get("transitions", {})
        self.risk_rules = load_yaml(resolve_config_path(risk_rules_path, "risk_rules.yaml")).get("chain_rules", {})
        self.security_knowledge = load_yaml(resolve_config_path(security_knowledge_path, "security_knowledge.yaml"))

    def evaluate_trace(self, sample: DatasetSample, mapper: Optional[ToolSemanticMapper] = None) -> AuditResult:
        intent = sample.intent_frame.model_copy(deep=True)
        if sample.user_query and not intent.constraints.get("user_query"):
            intent.constraints["user_query"] = sample.user_query
        return self.evaluate_tool_events(sample.id, intent, sample.trace, mapper=mapper)

    def evaluate_tool_events(
        self,
        sample_id: str,
        intent: IntentFrame,
        trace: List[ToolEvent],
        mapper: Optional[ToolSemanticMapper] = None,
    ) -> AuditResult:
        started_at = time.perf_counter()
        active_mapper = mapper or self.mapper
        state = TraceState()
        violations: List[Violation] = []
        semantic_events: List[SemanticEvent] = []
        for tool_event in trace:
            semantic_event = active_mapper.map_event(tool_event)
            semantic_events.append(semantic_event)
            violations.extend(self.evaluate_step(intent, state, semantic_event))
            state.update(semantic_event, intent)
        if self.switches.risk_graph_analysis:
            from traceshield_method.method.semantic import analyze_risk_graph

            violations.extend(
                analyze_risk_graph(
                    intent,
                    semantic_events,
                    self.security_knowledge,
                    include_sensitive_external=self.switches.sensitive_external_chain,
                    include_prompt_injection=self.switches.prompt_injection,
                    include_destructive_after_read=self.switches.destructive_after_read,
                )
            )
        latency_ms = (time.perf_counter() - started_at) * 1000
        return build_audit_result(sample_id, deduplicate_violations(violations), latency_ms)

    def evaluate_step(
        self,
        intent: IntentFrame,
        state: TraceState,
        event: SemanticEvent,
    ) -> List[Violation]:
        violations: List[Violation] = []
        if self.switches.capability_boundary:
            violations.extend(check_capability_boundary(intent, event))
        if self.switches.resource_boundary:
            violations.extend(check_resource_boundary(intent, event))

        authorized = self.switches.authorization_boundary and is_authorized_risky_call(intent, event)
        if self.switches.semantic_relation and not authorized:
            from traceshield_method.method.semantic import check_semantic_relation

            violations.extend(check_semantic_relation(intent, event, self.security_knowledge))
        if not authorized:
            if self.switches.step_transition:
                violations.extend(check_step_transition(intent, state, event, self.transition_rules))
            if self.switches.prompt_injection:
                violations.extend(check_prompt_injection_drift(state, event))

        if self.switches.sensitive_external_chain and not authorized:
            violations.extend(check_sensitive_external_chain(state, event))
        return violations


def deduplicate_violations(violations: List[Violation]) -> List[Violation]:
    by_path = {}
    for violation in violations:
        first_step = violation.evidence_steps[0] if violation.evidence_steps else None
        last_step = violation.evidence_steps[-1] if violation.evidence_steps else None
        path_key = (violation.violation_type, first_step, last_step, violation.target)
        previous = by_path.get(path_key)
        if previous is None or _prefer_violation(violation, previous):
            by_path[path_key] = violation

    seen = set()
    unique: List[Violation] = []
    for violation in by_path.values():
        exact_key = (violation.violation_type, tuple(violation.evidence_steps), violation.target)
        if exact_key not in seen:
            seen.add(exact_key)
            unique.append(violation)
    return unique


def _prefer_violation(candidate: Violation, current: Violation) -> bool:
    if len(candidate.evidence_steps) != len(current.evidence_steps):
        return len(candidate.evidence_steps) > len(current.evidence_steps)
    return _source_rank(candidate.source) < _source_rank(current.source)


def _source_rank(source: str | None) -> int:
    priority = {
        "risk_graph": 0,
        "sensitive_external_chain": 1,
        "prompt_injection": 2,
        "semantic_relation": 3,
        "resource_boundary": 4,
        "capability_boundary": 5,
        "step_transition": 6,
    }
    return priority.get(source or "", 99)
