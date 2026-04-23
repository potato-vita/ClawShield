from __future__ import annotations

from pydantic import BaseModel


class RulesSummary(BaseModel):
    task_tool_rule_count: int
    tool_resource_rule_count: int
    sensitive_resource_count: int
    risk_chain_rule_count: int
    version: str = "v1"
