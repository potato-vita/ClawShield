from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.policy.matchers.resource_matcher import match_resource_rules
from app.policy.matchers.task_matcher import match_task_rules
from app.policy.models import SensitiveResourceRule, TaskToolRule, ToolResourceRule


class PolicyMatchersTestCase(unittest.TestCase):
    def test_task_matcher_supports_glob_patterns(self) -> None:
        rules = [
            TaskToolRule(
                rule_id="task-analysis-glob",
                task_type="analysis",
                allowed_tools=["workspace_*", "summarizer"],
                denied_tools=["danger_*", "shell*"],
                reason="analysis should avoid risky tools",
                enabled=True,
            )
        ]

        denied = match_task_rules(task_type="analysis", tool_id="danger_exec_plugin", rules=rules)
        self.assertEqual(denied[0].decision, "deny")

        allowed = match_task_rules(task_type="analysis", tool_id="workspace_reader", rules=rules)
        self.assertEqual(allowed[0].decision, "allow")

        warned = match_task_rules(task_type="analysis", tool_id="http_fetcher", rules=rules)
        self.assertEqual(warned[0].decision, "warn")

    def test_sensitive_matcher_supports_exact_contains_regex(self) -> None:
        sensitive_rules = [
            SensitiveResourceRule(
                rule_id="env-exact",
                resource_type="env",
                match_type="exact",
                patterns=["OPENAI_API_KEY"],
                sensitivity_level="high",
                decision="deny",
                reason="exact env key is sensitive",
                labels=["credential"],
                enabled=True,
            ),
            SensitiveResourceRule(
                rule_id="file-contains",
                resource_type="file",
                match_type="contains",
                patterns=[".env"],
                sensitivity_level="high",
                decision="deny",
                reason="contains secret file marker",
                labels=["secret_file"],
                enabled=True,
            ),
            SensitiveResourceRule(
                rule_id="http-regex",
                resource_type="http",
                match_type="regex",
                patterns=[r"^https://(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?/"],
                sensitivity_level="medium",
                decision="warn",
                reason="raw ip endpoint",
                labels=["external_transfer"],
                enabled=True,
            ),
        ]

        env_match = match_resource_rules(
            tool_id="env_reader",
            resource_type="env",
            resource_id="OPENAI_API_KEY",
            resource_attributes={},
            tool_resource_rules=[],
            sensitive_rules=sensitive_rules,
        )
        self.assertTrue(any(item.rule_id == "env-exact" and item.decision == "deny" for item in env_match))

        file_match = match_resource_rules(
            tool_id="workspace_reader",
            resource_type="file",
            resource_id="./workspace/.env.local",
            resource_attributes={},
            tool_resource_rules=[],
            sensitive_rules=sensitive_rules,
        )
        self.assertTrue(any(item.rule_id == "file-contains" and item.decision == "deny" for item in file_match))

        http_match = match_resource_rules(
            tool_id="http_fetcher",
            resource_type="http",
            resource_id="https://10.20.30.40/upload",
            resource_attributes={},
            tool_resource_rules=[],
            sensitive_rules=sensitive_rules,
        )
        self.assertTrue(any(item.rule_id == "http-regex" and item.decision == "warn" for item in http_match))

    def test_http_tool_resource_rule_can_block_private_ip(self) -> None:
        http_rules = [
            ToolResourceRule(
                rule_id="http-egress",
                tool_id="http_fetcher",
                resource_type="http",
                block_private_networks=True,
                denied_methods=["DELETE"],
                allowed_methods=["GET", "POST"],
            )
        ]
        matches = match_resource_rules(
            tool_id="http_fetcher",
            resource_type="http",
            resource_id="https://10.10.10.10/upload",
            resource_attributes={"method": "POST"},
            tool_resource_rules=http_rules,
            sensitive_rules=[],
        )
        self.assertTrue(any(item.rule_id == "http-egress" and item.decision == "deny" for item in matches))

    def test_http_tool_resource_rule_can_match_wildcard_tool_id(self) -> None:
        http_rules = [
            ToolResourceRule(
                rule_id="http-wildcard",
                tool_id="*",
                resource_type="http",
                block_private_networks=True,
            )
        ]
        matches = match_resource_rules(
            tool_id="exec",
            resource_type="http",
            resource_id="https://10.0.0.8/upload",
            resource_attributes={"method": "POST"},
            tool_resource_rules=http_rules,
            sensitive_rules=[],
        )
        self.assertTrue(any(item.rule_id == "http-wildcard" and item.decision == "deny" for item in matches))


if __name__ == "__main__":
    unittest.main()
