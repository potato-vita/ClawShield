from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaskToolRule:
    rule_id: str
    task_type: str
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)
    reason: str = ""
    enabled: bool = True


@dataclass
class ToolResourceRule:
    rule_id: str
    tool_id: str
    resource_type: str
    allowed_patterns: list[str] = field(default_factory=list)
    denied_patterns: list[str] = field(default_factory=list)
    workspace_only: bool = False
    reason: str = ""
    enabled: bool = True


@dataclass
class SensitiveResourceRule:
    rule_id: str
    resource_type: str
    match_type: str
    patterns: list[str] = field(default_factory=list)
    sensitivity_level: str = "medium"
    labels: list[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class RiskChainRule:
    chain_id: str
    sequence: list[dict] = field(default_factory=list)
    window_seconds: int = 0
    risk_level: str = "medium"
    disposition: str = "warn"
    explain: str = ""
    enabled: bool = True


@dataclass
class MatchedRule:
    rule_id: str
    rule_type: str
    decision: str
    risk_level: str
    reason: str


@dataclass
class PolicyEvaluationResult:
    decision: str
    matched_rules: list[MatchedRule]
    risk_level: str
    disposition: str
    explanations: list[str]


@dataclass
class PolicyRulesBundle:
    task_tool_rules: list[TaskToolRule]
    tool_resource_rules: list[ToolResourceRule]
    sensitive_resource_rules: list[SensitiveResourceRule]
    risk_chain_rules: list[RiskChainRule]
