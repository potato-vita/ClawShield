from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


EvidenceNodeType = Literal["task", "tool", "resource", "risk", "disposition"]
EvidenceEdgeType = Literal["caused_by", "accessed", "triggered", "blocked_by", "follows"]


class EvidenceNode(BaseModel):
    node_id: str
    run_id: str
    source_event_id: str | None = None
    node_type: EvidenceNodeType
    title: str
    summary: str
    risk_level: str | None = None
    ts: datetime | None = None


class EvidenceEdge(BaseModel):
    edge_id: str
    run_id: str
    from_node_id: str
    to_node_id: str
    edge_type: EvidenceEdgeType
    label: str | None = None


class RiskFinding(BaseModel):
    chain_id: str
    name: str
    risk_level: str
    disposition: str
    reason: str
    event_ids: list[str]
    path_nodes: list[str]
