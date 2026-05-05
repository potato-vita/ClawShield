from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.schemas.evidence import EvidenceEdge, EvidenceNode
from app.services.audit_service import audit_service


class EvidenceBuilder:
    """Build evidence graph nodes and edges from run-level audit events."""

    _high_risk_levels = {"high", "critical", "severe"}

    def build(self, db: Session, run_id: str) -> tuple[list[EvidenceNode], list[EvidenceEdge]]:
        events = audit_service.list_events(
            db=db,
            run_id=run_id,
            limit=1000,
            offset=0,
            order="asc",
        )

        nodes: dict[str, EvidenceNode] = {}
        edges: dict[str, EvidenceEdge] = {}

        task_node_id = f"task:{run_id}"
        nodes[task_node_id] = EvidenceNode(
            node_id=task_node_id,
            run_id=run_id,
            node_type="task",
            title="Task",
            summary="Run-level task context",
            ts=events[0].ts if events else None,
        )
        goal_node_id = f"goal:{run_id}"
        nodes[goal_node_id] = EvidenceNode(
            node_id=goal_node_id,
            run_id=run_id,
            node_type="goal",
            title="Goal Contract",
            summary="Run-level target contract",
            ts=events[0].ts if events else None,
        )

        previous_anchor: str | None = None
        for event in events:
            tool_node_id = self._ensure_tool_node(nodes=nodes, run_id=run_id, event=event)
            intent_node_id = self._ensure_intent_node(nodes=nodes, run_id=run_id, event=event)
            resource_node_id = self._ensure_resource_node(nodes=nodes, run_id=run_id, event=event)
            risk_node_id = self._ensure_risk_node(nodes=nodes, run_id=run_id, event=event)
            disposition_node_id = self._ensure_disposition_node(nodes=nodes, run_id=run_id, event=event)
            step_node_id = self._ensure_step_node(nodes=nodes, run_id=run_id, event=event)
            alignment_node_id = self._ensure_alignment_node(nodes=nodes, run_id=run_id, event=event)
            impact_node_id = self._ensure_impact_node(nodes=nodes, run_id=run_id, event=event)

            self._add_edge(
                edges=edges,
                run_id=run_id,
                from_node_id=task_node_id,
                to_node_id=goal_node_id,
                edge_type="aligns_with",
                label="task to goal",
            )

            if step_node_id:
                self._add_edge(
                    edges=edges,
                    run_id=run_id,
                    from_node_id=goal_node_id,
                    to_node_id=step_node_id,
                    edge_type="caused_by",
                    label="goal drives step",
                )

            if intent_node_id:
                self._add_edge(
                    edges=edges,
                    run_id=run_id,
                    from_node_id=step_node_id or goal_node_id,
                    to_node_id=intent_node_id,
                    edge_type="caused_by",
                    label="step drives intent",
                )

            if tool_node_id:
                self._add_edge(
                    edges=edges,
                    run_id=run_id,
                    from_node_id=intent_node_id or step_node_id or task_node_id,
                    to_node_id=tool_node_id,
                    edge_type="caused_by",
                    label="task triggers tool call",
                )

            if resource_node_id:
                self._add_edge(
                    edges=edges,
                    run_id=run_id,
                    from_node_id=tool_node_id or task_node_id,
                    to_node_id=resource_node_id,
                    edge_type="accessed",
                    label=event.resource_type,
                )

            if impact_node_id and resource_node_id:
                self._add_edge(
                    edges=edges,
                    run_id=run_id,
                    from_node_id=resource_node_id,
                    to_node_id=impact_node_id,
                    edge_type="impacts",
                    label="resource impact",
                )
            elif impact_node_id and intent_node_id:
                self._add_edge(
                    edges=edges,
                    run_id=run_id,
                    from_node_id=intent_node_id,
                    to_node_id=impact_node_id,
                    edge_type="impacts",
                    label="intent impact",
                )

            if alignment_node_id:
                self._add_edge(
                    edges=edges,
                    run_id=run_id,
                    from_node_id=impact_node_id or resource_node_id or tool_node_id or task_node_id,
                    to_node_id=alignment_node_id,
                    edge_type="aligns_with",
                    label="alignment decision",
                )

            if risk_node_id:
                self._add_edge(
                    edges=edges,
                    run_id=run_id,
                    from_node_id=alignment_node_id or impact_node_id or resource_node_id or tool_node_id or task_node_id,
                    to_node_id=risk_node_id,
                    edge_type="triggered",
                    label=event.event_type,
                )

            if disposition_node_id:
                self._add_edge(
                    edges=edges,
                    run_id=run_id,
                    from_node_id=risk_node_id or tool_node_id or task_node_id,
                    to_node_id=disposition_node_id,
                    edge_type="blocked_by",
                    label=event.disposition,
                )

            anchor_candidates: list[str | None] = [
                disposition_node_id,
                risk_node_id,
                alignment_node_id,
                impact_node_id,
                resource_node_id,
                intent_node_id,
                tool_node_id,
                step_node_id,
                task_node_id,
            ]
            current_anchor = self._first_not_none(anchor_candidates)
            if previous_anchor and current_anchor and previous_anchor != current_anchor:
                self._add_edge(
                    edges=edges,
                    run_id=run_id,
                    from_node_id=previous_anchor,
                    to_node_id=current_anchor,
                    edge_type="follows",
                    label="event sequence",
                )
            previous_anchor = current_anchor

        return list(nodes.values()), list(edges.values())

    @staticmethod
    def _first_not_none(values: Iterable[str | None]) -> str | None:
        for value in values:
            if value:
                return value
        return None

    def _ensure_tool_node(self, nodes: dict[str, EvidenceNode], run_id: str, event) -> str | None:
        if not event.tool_id:
            return None

        node_id = f"tool:{event.tool_id}"
        if node_id not in nodes:
            nodes[node_id] = EvidenceNode(
                node_id=node_id,
                run_id=run_id,
                source_event_id=event.event_id,
                node_type="tool",
                title=event.tool_id,
                summary="Tool invocation",
                ts=event.ts,
            )
        return node_id

    def _ensure_intent_node(self, nodes: dict[str, EvidenceNode], run_id: str, event) -> str | None:
        if not event.tool_call_id and not event.intended_effect:
            return None
        intent_id = event.tool_call_id or event.event_id
        node_id = f"intent:{intent_id}"
        if node_id not in nodes:
            nodes[node_id] = EvidenceNode(
                node_id=node_id,
                run_id=run_id,
                source_event_id=event.event_id,
                node_type="intent",
                title=event.intended_effect or "intent",
                summary="Planned semantic intent",
                ts=event.ts,
            )
        return node_id

    def _ensure_step_node(self, nodes: dict[str, EvidenceNode], run_id: str, event) -> str | None:
        if not event.step_id:
            return None
        node_id = f"step:{event.step_id}"
        if node_id not in nodes:
            nodes[node_id] = EvidenceNode(
                node_id=node_id,
                run_id=run_id,
                source_event_id=event.event_id,
                node_type="step",
                title=event.step_id,
                summary="Task step state",
                ts=event.ts,
            )
        return node_id

    def _ensure_alignment_node(self, nodes: dict[str, EvidenceNode], run_id: str, event) -> str | None:
        if not event.alignment_decision:
            return None
        node_id = f"alignment:{event.event_id}"
        if node_id not in nodes:
            nodes[node_id] = EvidenceNode(
                node_id=node_id,
                run_id=run_id,
                source_event_id=event.event_id,
                node_type="alignment",
                title=f"alignment:{event.alignment_decision}",
                summary=event.alignment_reason or "alignment decision",
                risk_level=event.risk_level,
                ts=event.ts,
            )
        return node_id

    def _ensure_impact_node(self, nodes: dict[str, EvidenceNode], run_id: str, event) -> str | None:
        if not event.impact_level and not event.intended_effect:
            return None
        node_id = f"impact:{event.event_id}"
        if node_id not in nodes:
            nodes[node_id] = EvidenceNode(
                node_id=node_id,
                run_id=run_id,
                source_event_id=event.event_id,
                node_type="impact",
                title=f"impact:{event.impact_level or 'unknown'}",
                summary=event.intended_effect or "impact assessment",
                risk_level=event.risk_level,
                ts=event.ts,
            )
        return node_id

    def _ensure_resource_node(self, nodes: dict[str, EvidenceNode], run_id: str, event) -> str | None:
        if not event.resource_type and not event.resource_id:
            return None

        resource_type = event.resource_type or "unknown"
        resource_id = event.resource_id or "unknown"
        node_id = f"resource:{resource_type}:{resource_id}"
        if node_id not in nodes:
            nodes[node_id] = EvidenceNode(
                node_id=node_id,
                run_id=run_id,
                source_event_id=event.event_id,
                node_type="resource",
                title=f"{resource_type}:{resource_id}",
                summary="Resource access",
                ts=event.ts,
            )
        return node_id

    def _ensure_risk_node(self, nodes: dict[str, EvidenceNode], run_id: str, event) -> str | None:
        risk_level = (event.risk_level or "").lower()
        is_chain_or_rule = event.event_type in {"risk_rule_matched", "risk_chain_formed"}
        if not is_chain_or_rule and risk_level not in self._high_risk_levels:
            return None

        node_id = f"risk:{event.event_id}"
        if node_id not in nodes:
            nodes[node_id] = EvidenceNode(
                node_id=node_id,
                run_id=run_id,
                source_event_id=event.event_id,
                node_type="risk",
                title=f"risk:{event.risk_level or 'unknown'}",
                summary=event.event_type,
                risk_level=event.risk_level,
                ts=event.ts,
            )
        return node_id

    def _ensure_disposition_node(self, nodes: dict[str, EvidenceNode], run_id: str, event) -> str | None:
        disposition = (event.disposition or "").lower()
        if event.event_type != "disposition_applied" and disposition not in {"deny", "block"}:
            return None

        node_id = f"disposition:{event.event_id}"
        if node_id not in nodes:
            nodes[node_id] = EvidenceNode(
                node_id=node_id,
                run_id=run_id,
                source_event_id=event.event_id,
                node_type="disposition",
                title=event.disposition or "disposition",
                summary="Final handling applied",
                risk_level=event.risk_level,
                ts=event.ts,
            )
        return node_id

    @staticmethod
    def _add_edge(
        edges: dict[str, EvidenceEdge],
        run_id: str,
        from_node_id: str,
        to_node_id: str,
        edge_type: str,
        label: str | None,
    ) -> None:
        edge_id = f"{from_node_id}|{edge_type}|{to_node_id}"
        if edge_id in edges:
            return

        edges[edge_id] = EvidenceEdge(
            edge_id=edge_id,
            run_id=run_id,
            from_node_id=from_node_id,
            to_node_id=to_node_id,
            edge_type=edge_type,  # type: ignore[arg-type]
            label=label,
        )


evidence_builder = EvidenceBuilder()
