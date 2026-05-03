from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.policy.matchers.task_matcher import match_task_rules
from app.policy.models import TaskToolRule


class TaskRuleMatcherTestCase(unittest.TestCase):
    def test_wildcard_denied_tool_pattern_blocks_tool(self) -> None:
        rules = [
            TaskToolRule(
                rule_id="analysis-deny-pattern",
                task_type="analysis",
                denied_tools=["danger_*"],
                allowed_tools=[],
                reason="deny wildcard tools",
                enabled=True,
            )
        ]
        matched = match_task_rules(task_type="analysis", tool_id="danger_exec_plugin", rules=rules)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].decision, "deny")

    def test_allowed_list_with_wildcard_accepts_matching_tool(self) -> None:
        rules = [
            TaskToolRule(
                rule_id="analysis-allow-pattern",
                task_type="analysis",
                denied_tools=[],
                allowed_tools=["workspace_*"],
                reason="allow workspace tools",
                enabled=True,
            )
        ]
        matched = match_task_rules(task_type="analysis", tool_id="workspace_reader", rules=rules)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].decision, "allow")

    def test_allowed_list_with_wildcard_warns_for_non_matching_tool(self) -> None:
        rules = [
            TaskToolRule(
                rule_id="analysis-allow-pattern",
                task_type="analysis",
                denied_tools=[],
                allowed_tools=["workspace_*"],
                reason="allow workspace tools",
                enabled=True,
            )
        ]
        matched = match_task_rules(task_type="analysis", tool_id="http_fetcher", rules=rules)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].decision, "warn")


if __name__ == "__main__":
    unittest.main()
