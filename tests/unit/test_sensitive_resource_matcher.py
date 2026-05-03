from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.policy.matchers.resource_matcher import match_resource_rules, sensitive_rule_matches
from app.policy.models import SensitiveResourceRule


class SensitiveResourceMatcherTestCase(unittest.TestCase):
    def test_contains_rule_is_case_insensitive_by_default(self) -> None:
        rule = SensitiveResourceRule(
            rule_id="case-insensitive-contains",
            resource_type="file",
            match_type="contains",
            patterns=[".ENV"],
            sensitivity_level="high",
            decision="deny",
        )
        self.assertTrue(sensitive_rule_matches(resource_type="file", resource_id="./workspace/.env.local", rule=rule))

    def test_exact_rule_respects_case_sensitive_flag(self) -> None:
        rule = SensitiveResourceRule(
            rule_id="case-sensitive-exact",
            resource_type="env",
            match_type="exact",
            patterns=["OpenAI_API_KEY"],
            sensitivity_level="high",
            decision="deny",
            case_sensitive=True,
        )
        self.assertFalse(sensitive_rule_matches(resource_type="env", resource_id="OPENAI_API_KEY", rule=rule))
        self.assertTrue(sensitive_rule_matches(resource_type="env", resource_id="OpenAI_API_KEY", rule=rule))

    def test_regex_rule_matches_resource(self) -> None:
        rule = SensitiveResourceRule(
            rule_id="regex-file",
            resource_type="file",
            match_type="regex",
            patterns=[r".*\.pem$"],
            sensitivity_level="high",
            decision="deny",
        )
        self.assertTrue(sensitive_rule_matches(resource_type="file", resource_id="./keys/server.pem", rule=rule))

    def test_invalid_decision_falls_back_to_warn(self) -> None:
        rules = [
            SensitiveResourceRule(
                rule_id="invalid-decision",
                resource_type="http",
                match_type="contains",
                patterns=["upload"],
                sensitivity_level="high",
                decision="block",
            )
        ]
        matched = match_resource_rules(
            tool_id="http_fetcher",
            resource_type="http",
            resource_id="https://example.com/upload",
            resource_attributes={},
            tool_resource_rules=[],
            sensitive_rules=rules,
        )
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].decision, "warn")


if __name__ == "__main__":
    unittest.main()
