from typing import Any, Iterable, List

from traceshield_method.method.schemas import SemanticEvent, Violation
from traceshield_method.method.state import TraceState


NETWORK_ACTIONS = {"network_post", "external_send"}


def check_sensitive_external_chain(state: TraceState, event: SemanticEvent) -> List[Violation]:
    if not state.sensitive_resources_read:
        return []
    if event.tool_type == "network" or event.semantic_action in NETWORK_ACTIONS:
        sensitive_step, sensitive_resource = state.sensitive_resources_read[-1]
        if _event_excludes_or_omits_source(event, sensitive_resource):
            return []
        if _event_declares_sources(event) and not _event_declares_source(event, sensitive_resource):
            return []
        return [
            Violation(
                violation_type="chain_semantic_drift",
                evidence_steps=[sensitive_step, event.step_id],
                target=event.target_resource,
                source="sensitive_external_chain",
                reason=(
                    f"执行链先读取敏感资源 {sensitive_resource}，随后向外部地址发送数据，"
                    "形成敏感读取后外联的语义漂移链。"
                ),
            )
        ]
    return []


def _event_declares_sources(event: SemanticEvent) -> bool:
    return bool(_declared_refs(event, ("input_sources", "source_refs", "content_sources", "used_sources", "provenance_sources")))


def _event_declares_source(event: SemanticEvent, resource: str) -> bool:
    return _refs_match(resource, _declared_refs(event, ("input_sources", "source_refs", "content_sources", "used_sources", "provenance_sources")))


def _event_excludes_or_omits_source(event: SemanticEvent, resource: str) -> bool:
    return _refs_match(resource, _declared_refs(event, ("excluded_sources", "excluded_resources", "omitted_sources", "omitted_resources")))


def _declared_refs(event: SemanticEvent, keys: Iterable[str]) -> set[str]:
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


def _refs_match(resource: str, refs: set[str]) -> bool:
    resource = str(resource).strip().lower()
    return any(ref == resource or ref in resource or resource in ref for ref in refs)
