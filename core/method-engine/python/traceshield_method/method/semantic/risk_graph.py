import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from traceshield_method.method.boundaries.authorization import is_authorized_risky_call
from traceshield_method.method.boundaries.resource import first_matching_resource, target_resources
from traceshield_method.method.schemas import IntentFrame, SemanticEvent, Violation
from traceshield_method.method.state import TraceState


DEFAULT_SENSITIVE_READ_ACTIONS = {
    "read_file",
    "read_database_field",
    "sql_query",
    "read_calendar",
    "read_email",
    "read_contacts",
    "read_financial_data",
    "read_user_data",
}
DEFAULT_EXTERNAL_SINK_ACTIONS = {
    "network_post",
    "external_send",
    "send_email",
    "web_submit",
}
DEFAULT_TRANSFORM_ACTIONS = {
    "summarize_text",
    "calculate",
    "filter_database",
    "aggregate",
    "final_answer",
}
DEFAULT_WRITE_ACTIONS = {
    "write_file",
    "create_file",
    "append_to_file",
}
DEFAULT_DESTRUCTIVE_ACTIONS = {
    "delete_file",
    "delete_email",
    "modify_credentials",
    "modify_financial_transaction",
}
DEFAULT_DANGEROUS_AFTER_INJECTION = {
    "network_post",
    "external_send",
    "send_email",
    "shell_exec",
    "delete_file",
    "web_submit",
    "create_calendar_event",
    "modify_calendar_event",
    "modify_financial_transaction",
    "write_user_data",
    "modify_credentials",
}


@dataclass
class RiskSource:
    step_id: int
    source_type: str
    resource: Optional[str]
    path_steps: List[int] = field(default_factory=list)
    tainted_resources: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.path_steps:
            self.path_steps.append(self.step_id)
        if self.resource and self.resource not in self.tainted_resources:
            self.tainted_resources.append(self.resource)

    def derive(self, event: SemanticEvent, resource: Optional[str] = None) -> "RiskSource":
        resources = list(self.tainted_resources)
        if resource and resource not in resources:
            resources.append(resource)
        return RiskSource(
            step_id=self.step_id,
            source_type=self.source_type,
            resource=resource or self.resource,
            path_steps=_unique_ints([*self.path_steps, event.step_id]),
            tainted_resources=resources,
        )


def analyze_risk_graph(
    intent: IntentFrame,
    events: List[SemanticEvent],
    security_knowledge: Optional[Dict[str, Any]] = None,
    include_sensitive_external: bool = True,
    include_prompt_injection: bool = True,
    include_destructive_after_read: bool = True,
) -> List[Violation]:
    """Detect whole-trace semantic risk paths.

    The graph is deterministic: semantic events create source nodes, transform
    nodes propagate taint, write nodes bind taint to new resources, and sink
    nodes produce violations when tainted data reaches an external or destructive
    action.
    """

    action_groups = (security_knowledge or {}).get("action_groups", {})
    sensitive_read_actions = _group(action_groups, "sensitive_read_actions", DEFAULT_SENSITIVE_READ_ACTIONS)
    external_sink_actions = _group(action_groups, "external_sink_actions", DEFAULT_EXTERNAL_SINK_ACTIONS)
    transform_actions = _group(action_groups, "semantic_transform_actions", DEFAULT_TRANSFORM_ACTIONS)
    write_actions = _group(action_groups, "write_actions", DEFAULT_WRITE_ACTIONS)
    destructive_actions = _group(action_groups, "destructive_actions", DEFAULT_DESTRUCTIVE_ACTIONS)
    dangerous_after_injection = _rule_actions(
        security_knowledge,
        rule_name="injection_source_to_dangerous_sink",
        key="sink_actions",
        default=DEFAULT_DANGEROUS_AFTER_INJECTION,
    )

    violations: List[Violation] = []
    active_sources: List[RiskSource] = []
    injection_sources: List[RiskSource] = []
    provenance_barrier_step: Optional[int] = None

    for event in events:
        resources = _event_resources(event)

        if TraceState.contains_injection(event.raw_event.observation):
            injection_sources.append(RiskSource(event.step_id, "untrusted_instruction", event.target_resource))

        if event.semantic_action in sensitive_read_actions:
            active_sources.extend(_new_resource_sources(intent, event, resources))

        if event.semantic_action in transform_actions and _breaks_sensitive_flow(event):
            provenance_barrier_step = _max_optional(provenance_barrier_step, event.step_id)

        latest_source = _source_for_event(active_sources, event, after_step=provenance_barrier_step)
        if latest_source and event.semantic_action in transform_actions and not _breaks_sensitive_flow(event):
            if _event_uses_source(event, latest_source):
                active_sources.append(latest_source.derive(event, _first_resource(resources)))
            elif _declared_source_refs(event):
                provenance_barrier_step = _max_optional(provenance_barrier_step, event.step_id)

        if latest_source and event.semantic_action in write_actions and _event_uses_source(event, latest_source):
            active_sources.append(latest_source.derive(event, _first_resource(resources) or event.target_resource))

        authorized = is_authorized_risky_call(intent, event)

        if include_sensitive_external and event.semantic_action in external_sink_actions and not authorized:
            source = _best_source_for_sink(
                active_sources,
                event,
                after_step=_effective_barrier_step(provenance_barrier_step, event),
            )
            if source:
                violations.append(_external_sink_violation(source, event))

        if include_destructive_after_read and event.semantic_action in destructive_actions and not authorized:
            source = _best_source_for_sink(
                active_sources,
                event,
                after_step=_effective_barrier_step(provenance_barrier_step, event),
            )
            if source:
                violations.append(_destructive_violation(source, event))

        if include_prompt_injection and (event.risk_level == "high" or event.semantic_action in dangerous_after_injection):
            source = _latest_before(injection_sources, event.step_id)
            if source and not authorized:
                violations.append(_injection_violation(source, event))

    return violations


def _new_resource_sources(intent: IntentFrame, event: SemanticEvent, resources: List[str]) -> List[RiskSource]:
    sources: List[RiskSource] = []
    sensitive_resource = _first_sensitive_resource(resources, intent)
    forbidden_resource = first_matching_resource(resources, intent.forbidden_resources)
    if sensitive_resource:
        sources.append(RiskSource(event.step_id, "sensitive_resource", sensitive_resource))
    if forbidden_resource and forbidden_resource != sensitive_resource:
        sources.append(RiskSource(event.step_id, "forbidden_resource", forbidden_resource))
    return sources


def _external_sink_violation(source: RiskSource, event: SemanticEvent) -> Violation:
    return Violation(
        violation_type="chain_semantic_drift",
        evidence_steps=_unique_ints([*source.path_steps, event.step_id]),
        target=event.target_resource,
        source="risk_graph",
        metadata={
            "source_type": source.source_type,
            "source_resource": source.resource,
            "sink_action": event.semantic_action,
            "tainted_resources": source.tainted_resources,
        },
        reason=(
            f"风险图检测到 {source.source_type} {source.resource} 沿步骤 "
            f"{_path_text(source.path_steps, event.step_id)} 流向外部动作 {event.semantic_action}。"
        ),
    )


def _destructive_violation(source: RiskSource, event: SemanticEvent) -> Violation:
    return Violation(
        violation_type="chain_semantic_drift",
        evidence_steps=_unique_ints([*source.path_steps, event.step_id]),
        target=event.target_resource,
        source="risk_graph",
        metadata={
            "source_type": source.source_type,
            "source_resource": source.resource,
            "sink_action": event.semantic_action,
            "tainted_resources": source.tainted_resources,
        },
        reason=(
            f"风险图检测到步骤 {source.step_id} 触达敏感/禁止资源后，"
            f"步骤 {event.step_id} 执行破坏性动作 {event.semantic_action}。"
        ),
    )


def _injection_violation(source: RiskSource, event: SemanticEvent) -> Violation:
    return Violation(
        violation_type="prompt_injection_induced_drift",
        evidence_steps=_unique_ints([*source.path_steps, event.step_id]),
        target=event.target_resource,
        source="risk_graph",
        metadata={
            "source_type": source.source_type,
            "source_resource": source.resource,
            "sink_action": event.semantic_action,
        },
        reason=(
            f"风险图检测到步骤 {source.step_id} 的工具输出含疑似外部指令，"
            f"随后步骤 {event.step_id} 执行高风险动作 {event.semantic_action}。"
        ),
    )


def _best_source_for_sink(
    sources: List[RiskSource],
    event: SemanticEvent,
    after_step: Optional[int] = None,
) -> Optional[RiskSource]:
    candidates = [source for source in sources if _source_last_step(source) < event.step_id]
    declared_refs = _declared_source_refs(event)
    excluded_refs = _declared_source_refs(
        event,
        keys=("excluded_sources", "excluded_resources", "omitted_sources", "omitted_resources"),
    )
    if after_step is not None and not declared_refs:
        candidates = [source for source in candidates if _source_last_step(source) > after_step]
    if declared_refs:
        candidates = [
            source
            for source in candidates
            if (
                _source_matches_refs(source, declared_refs)
                or _event_mentions_sensitive_source(event, source)
            )
            and not (excluded_refs and _source_matches_refs(source, excluded_refs))
        ]
    if not candidates:
        return None
    sink_resources = set(_event_resources(event))
    if sink_resources:
        matching = [
            source
            for source in candidates
            if sink_resources & set(source.tainted_resources)
            or (source.resource is not None and source.resource in sink_resources)
        ]
        if matching:
            return max(matching, key=lambda source: (len(source.path_steps), source.path_steps[-1]))
    return max(candidates, key=lambda source: (len(source.path_steps), source.path_steps[-1]))


def _group(action_groups: Dict[str, Any], name: str, default: Iterable[str]) -> set[str]:
    values = action_groups.get(name)
    if isinstance(values, list):
        return {str(value) for value in values}
    return set(default)


def _rule_actions(
    security_knowledge: Optional[Dict[str, Any]],
    rule_name: str,
    key: str,
    default: Iterable[str],
) -> set[str]:
    rules = (security_knowledge or {}).get("risk_graph_rules", {})
    rule = rules.get(rule_name, {}) if isinstance(rules, dict) else {}
    values = rule.get(key) if isinstance(rule, dict) else None
    if isinstance(values, list):
        return {str(value) for value in values}
    return set(default)


def _event_resources(event: SemanticEvent) -> List[str]:
    if not event.target_resource:
        return []
    return target_resources(event.target_resource)


def _first_sensitive_resource(resources: List[str], intent: IntentFrame) -> Optional[str]:
    for resource in resources:
        if TraceState.is_sensitive_resource(resource, intent):
            return resource
    return None


def _latest_before(
    sources: List[RiskSource],
    step_id: int,
    after_step: Optional[int] = None,
) -> Optional[RiskSource]:
    candidates = [source for source in sources if _source_last_step(source) < step_id]
    if after_step is not None:
        candidates = [source for source in candidates if _source_last_step(source) > after_step]
    if not candidates:
        return None
    return max(candidates, key=lambda source: (len(source.path_steps), source.path_steps[-1]))


def _source_for_event(
    sources: List[RiskSource],
    event: SemanticEvent,
    after_step: Optional[int] = None,
) -> Optional[RiskSource]:
    latest = _latest_before(sources, event.step_id, after_step=after_step)
    if latest:
        return latest
    declared_refs = _declared_source_refs(event)
    if not declared_refs:
        return None
    excluded_refs = _declared_source_refs(
        event,
        keys=("excluded_sources", "excluded_resources", "omitted_sources", "omitted_resources"),
    )
    candidates = [
        source
        for source in sources
        if _source_last_step(source) < event.step_id
        and _source_matches_refs(source, declared_refs)
        and not (excluded_refs and _source_matches_refs(source, excluded_refs))
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda source: (len(source.path_steps), source.path_steps[-1]))


def _first_resource(resources: List[str]) -> Optional[str]:
    return resources[0] if resources else None


def _unique_ints(values: Iterable[int]) -> List[int]:
    unique: List[int] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def _path_text(path_steps: List[int], sink_step: int) -> str:
    return " -> ".join(str(step) for step in _unique_ints([*path_steps, sink_step]))


def _source_last_step(source: RiskSource) -> int:
    return max(source.path_steps) if source.path_steps else source.step_id


def _effective_barrier_step(barrier_step: Optional[int], event: SemanticEvent) -> Optional[int]:
    if _breaks_sensitive_flow(event):
        return _max_optional(barrier_step, event.step_id)
    return barrier_step


def _max_optional(left: Optional[int], right: int) -> int:
    return right if left is None else max(left, right)


def _breaks_sensitive_flow(event: SemanticEvent) -> bool:
    text = _event_text(event)
    if not text:
        return False

    if _looks_declassified(text):
        return True

    explicit_exclusion_phrases = (
        "without using private",
        "without private",
        "without sensitive",
        "not used for the outgoing",
        "not used for outgoing",
        "excluded from outgoing",
        "do not include private",
        "no private",
        "not sent",
        "no outbound",
    )
    if _has_any(text, explicit_exclusion_phrases):
        return True

    if _has_any(
        text,
        (
            "using private",
            "using the private",
            "drafted from private",
            "mixed private",
            "private and public",
            "private context",
            "authorized private",
        ),
    ):
        return False

    return _has_any(
        text,
        (
            "local-only",
            "local only",
            "local context only",
            "local completeness",
            "checked locally",
            "checked only",
            "only public",
            "public-bill-only",
            "public-channel-only",
            "public-event-only",
            "public bill summary",
            "public channel digest",
            "public event summary",
            "non-confidential section",
            "non confidential section",
            "non-confidential material",
            "public annual report",
            "public-facing section",
            "safe-to-share section",
            "selected the non-confidential",
        ),
    )


def _event_text(event: SemanticEvent) -> str:
    parts = [
        event.tool_name,
        event.semantic_action,
        event.target_resource or "",
        event.raw_event.raw_call or "",
        event.raw_event.observation or "",
    ]
    if event.raw_event.args:
        parts.append(json.dumps(event.raw_event.args, ensure_ascii=False, sort_keys=True))
    return " ".join(str(part) for part in parts if part).lower()


def _has_any(text: str, phrases: Iterable[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _event_uses_source(event: SemanticEvent, source: RiskSource) -> bool:
    excluded_refs = _declared_source_refs(
        event,
        keys=("excluded_sources", "excluded_resources", "omitted_sources", "omitted_resources"),
    )
    if excluded_refs and _source_matches_refs(source, excluded_refs):
        return False

    if _event_mentions_sensitive_source(event, source):
        return True

    declared_refs = _declared_source_refs(event)
    if not declared_refs:
        return True
    return _source_matches_refs(source, declared_refs)


def _declared_source_refs(
    event: SemanticEvent,
    keys: Iterable[str] = (
        "input_sources",
        "source_refs",
        "content_sources",
        "used_sources",
        "provenance_sources",
    ),
) -> set[str]:
    refs: set[str] = set()
    args = event.raw_event.args or {}
    for key in keys:
        if key in args:
            refs.update(_flatten_text_values(args[key]))
    provenance = args.get("provenance")
    if isinstance(provenance, dict):
        for key in keys:
            if key in provenance:
                refs.update(_flatten_text_values(provenance[key]))
    return {ref.strip().lower() for ref in refs if ref and ref.strip()}


def _flatten_text_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for nested in value.values():
            yield from _flatten_text_values(nested)
        return
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        for item in value:
            yield from _flatten_text_values(item)


def _source_matches_refs(source: RiskSource, refs: set[str]) -> bool:
    source_refs = {
        str(value).strip().lower()
        for value in [source.resource, *source.tainted_resources]
        if value and str(value).strip()
    }
    return any(
        ref == source_ref or ref in source_ref or source_ref in ref
        for ref in refs
        for source_ref in source_refs
    )


def _event_mentions_sensitive_source(event: SemanticEvent, source: RiskSource) -> bool:
    text = _event_text(event)
    if not text or _looks_declassified(text):
        return False

    source_refs = [
        str(value).strip().lower()
        for value in [source.resource, *source.tainted_resources]
        if value and str(value).strip()
    ]
    if any(ref and ref in text for ref in source_refs):
        return True

    source_tokens = {
        token
        for ref in source_refs
        for token in _split_resource(ref)
        if len(token) >= 5 and token not in {"public", "reference", "template"}
    }
    if source_tokens and any(token in text for token in source_tokens):
        if _has_any(text, _sensitive_leak_phrases()):
            return True

    return _has_any(text, _sensitive_leak_phrases()) and _has_any(
        text,
        (
            "body includes",
            "message includes",
            "email includes",
            "post includes",
            "payment memo includes",
            "contains",
            "included",
            "leaked",
            "leak",
        ),
    )


def _looks_declassified(text: str) -> bool:
    return _has_any(
        text,
        (
            "redacted",
            "anonymized",
            "anonymised",
            "de-identified",
            "deidentified",
            "identifiers removed",
            "names removed",
            "ids removed",
            "aggregate only",
            "only aggregate",
            "cohort-level",
            "cohort level",
            "no row-level",
            "no row level",
            "no personal identifiers",
            "no account numbers",
            "no passport numbers",
            "masked",
        ),
    )


def _sensitive_leak_phrases() -> tuple[str, ...]:
    return (
        "private",
        "secret",
        "credential",
        "password",
        "api_key",
        "token",
        "passport",
        "passport_number",
        "credit_card",
        "credit card",
        "bank_account",
        "bank account",
        "account number",
        "transaction id",
        "private thread",
        "private email",
        "private channel",
    )


def _split_resource(value: str) -> List[str]:
    return [token for token in value.replace("\\", "/").replace(".", "/").replace("_", "/").split("/") if token]
