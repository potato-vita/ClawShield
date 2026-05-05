from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TimelineItem(BaseModel):
    ts: datetime
    title: str
    summary: str
    event_type: str
    risk_level: str | None = None
    disposition: str | None = None
    related_ids: list[str] = Field(default_factory=list)


class GraphNode(BaseModel):
    node_id: str
    node_type: str
    label: str
    risk_level: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    from_node_id: str
    to_node_id: str
    edge_type: str
    label: str | None = None


class GraphPayload(BaseModel):
    run_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    highlighted_paths: list[list[str]] = Field(default_factory=list)
