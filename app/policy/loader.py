from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.policy.models import (
    PolicyRulesBundle,
    RiskChainRule,
    SensitiveResourceRule,
    TaskToolRule,
    ToolResourceRule,
)


class PolicyLoader:
    """Load policy rules from configs/rules YAML files."""

    def __init__(self, rules_root: Path | None = None) -> None:
        default_root = Path(__file__).resolve().parents[2] / "configs" / "rules"
        self._rules_root = rules_root or default_root

    def _load_yaml(self, file_name: str) -> dict[str, Any]:
        file_path = self._rules_root / file_name
        if not file_path.exists():
            raise RuntimeError(f"policy file not found: {file_path}")

        with file_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}

        if not isinstance(loaded, dict):
            raise RuntimeError(f"policy file must contain a mapping: {file_path}")
        return loaded

    @staticmethod
    def _rules_list(loaded: dict[str, Any], file_name: str) -> list[dict[str, Any]]:
        rules = loaded.get("rules", [])
        if not isinstance(rules, list):
            raise RuntimeError(f"rules must be a list in {file_name}")
        return [item for item in rules if isinstance(item, dict)]

    def load(self) -> PolicyRulesBundle:
        task_tool_raw = self._load_yaml("task_tool_map.yaml")
        tool_resource_raw = self._load_yaml("tool_resource_map.yaml")
        sensitive_raw = self._load_yaml("sensitive_resources.yaml")
        risk_chain_raw = self._load_yaml("risk_chains.yaml")

        task_tool_rules = [
            TaskToolRule(
                rule_id=str(item.get("rule_id", "")),
                task_type=str(item.get("task_type", "unknown")),
                allowed_tools=[str(v) for v in item.get("allowed_tools", [])],
                denied_tools=[str(v) for v in item.get("denied_tools", [])],
                reason=str(item.get("reason", "")),
                enabled=bool(item.get("enabled", True)),
            )
            for item in self._rules_list(task_tool_raw, "task_tool_map.yaml")
        ]

        tool_resource_rules = [
            ToolResourceRule(
                rule_id=str(item.get("rule_id", "")),
                tool_id=str(item.get("tool_id", "")),
                resource_type=str(item.get("resource_type", "")),
                allowed_patterns=[str(v) for v in item.get("allowed_patterns", [])],
                denied_patterns=[str(v) for v in item.get("denied_patterns", [])],
                workspace_only=bool(item.get("workspace_only", False)),
                reason=str(item.get("reason", "")),
                enabled=bool(item.get("enabled", True)),
            )
            for item in self._rules_list(tool_resource_raw, "tool_resource_map.yaml")
        ]

        sensitive_rules = [
            SensitiveResourceRule(
                rule_id=str(item.get("rule_id", "")),
                resource_type=str(item.get("resource_type", "")),
                match_type=str(item.get("match_type", "pattern")),
                patterns=[str(v) for v in item.get("patterns", [])],
                sensitivity_level=str(item.get("sensitivity_level", "medium")),
                labels=[str(v) for v in item.get("labels", [])],
                enabled=bool(item.get("enabled", True)),
            )
            for item in self._rules_list(sensitive_raw, "sensitive_resources.yaml")
        ]

        risk_chain_rules = [
            RiskChainRule(
                chain_id=str(item.get("chain_id", "")),
                sequence=list(item.get("sequence", [])) if isinstance(item.get("sequence", []), list) else [],
                window_seconds=int(item.get("window_seconds", 0)),
                risk_level=str(item.get("risk_level", "medium")),
                disposition=str(item.get("disposition", "warn")),
                explain=str(item.get("explain", "")),
                enabled=bool(item.get("enabled", True)),
            )
            for item in self._rules_list(risk_chain_raw, "risk_chains.yaml")
        ]

        return PolicyRulesBundle(
            task_tool_rules=task_tool_rules,
            tool_resource_rules=tool_resource_rules,
            sensitive_resource_rules=sensitive_rules,
            risk_chain_rules=risk_chain_rules,
        )
