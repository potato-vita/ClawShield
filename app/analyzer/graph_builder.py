from __future__ import annotations

from app.schemas.evidence import EvidenceEdge, EvidenceNode, RiskFinding
from app.schemas.graph import GraphEdge, GraphNode, GraphPayload


class GraphBuilder:
    """Transform evidence graph structures into API-ready graph payload."""

    def build(
        self,
        run_id: str,
        nodes: list[EvidenceNode],
        edges: list[EvidenceEdge],
        findings: list[RiskFinding],
    ) -> dict[str, object]:
        graph_payload = GraphPayload(
            run_id=run_id,
            nodes=[
                GraphNode(
                    node_id=node.node_id,
                    node_type=node.node_type,
                    label=node.title,
                    risk_level=node.risk_level,
                    metadata={
                        "summary": node.summary,
                        "source_event_id": node.source_event_id,
                        "ts": node.ts.isoformat() if node.ts else None,
                    },
                )
                for node in nodes
            ],
            edges=[
                GraphEdge(
                    from_node_id=edge.from_node_id,
                    to_node_id=edge.to_node_id,
                    edge_type=edge.edge_type,
                    label=edge.label,
                )
                for edge in edges
            ],
            highlighted_paths=[item.path_nodes for item in findings if item.path_nodes],
        )

        final_risk_level = self._max_risk([item.risk_level for item in findings])
        summary = {
            "finding_count": len(findings),
            "final_risk_level": final_risk_level,
            "chain_ids": [item.chain_id for item in findings],
        }

        return {
            "run_id": run_id,
            "nodes": [item.model_dump() for item in graph_payload.nodes],
            "edges": [item.model_dump() for item in graph_payload.edges],
            "highlighted_paths": graph_payload.highlighted_paths,
            "summary": summary,
            "risk_findings": [item.model_dump() for item in findings],
        }

    @staticmethod
    def _max_risk(levels: list[str]) -> str | None:
        if not levels:
            return None

        rank = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4,
            "severe": 4,
        }
        selected = "low"
        selected_rank = 0
        for level in levels:
            normalized = (level or "low").lower()
            current_rank = rank.get(normalized, 0)
            if current_rank > selected_rank:
                selected = normalized
                selected_rank = current_rank
        return selected if selected_rank > 0 else None


graph_builder = GraphBuilder()
