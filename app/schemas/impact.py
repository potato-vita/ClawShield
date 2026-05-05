from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ResourceImpact(BaseModel):
    resource_type: str
    resource_id: str
    sensitivity: str
    effect_type: str
    impact_level: str
    mutation_risk: bool
    exfiltration_risk: bool
    reason: str
    impact_signals: list[str] = Field(default_factory=list)
    domain_trust_level: str | None = None
    signal_details: dict[str, Any] = Field(default_factory=dict)
