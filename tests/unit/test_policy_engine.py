from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.policy.engine import policy_engine


class PolicyEngineTestCase(unittest.TestCase):
    def test_analysis_high_risk_tool_is_denied(self) -> None:
        result = policy_engine.evaluate(
            task_type="analysis",
            tool_id="danger_exec_plugin",
            resource_type="tool",
            resource_id="danger_exec_plugin",
        )
        self.assertEqual(result.decision, "deny")
        self.assertGreater(len(result.matched_rules), 0)
        self.assertTrue(any(line.startswith("[DENY|") for line in result.explanations))
        self.assertTrue(any("task-analysis-basic-tools" in line for line in result.explanations))

    def test_dropdown_tool_does_not_trigger_destructive_keyword_false_positive(self) -> None:
        result = policy_engine.evaluate(
            task_type="general",
            tool_id="dropdown_formatter",
            resource_type="tool",
            resource_id="dropdown_formatter",
        )
        self.assertEqual(result.decision, "allow")
        self.assertEqual(result.explanations, ["No policy rule matched; default allow."])


if __name__ == "__main__":
    unittest.main()
