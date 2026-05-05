from __future__ import annotations

from app.policy.disposition import decision_risk_level, decision_to_disposition
from app.policy.explain import render_explanations
from app.policy.loader import PolicyLoader
from app.policy.matchers.resource_matcher import match_resource_rules
from app.policy.matchers.task_matcher import match_task_rules
from app.policy.matchers.tool_matcher import match_tool_rules
from app.policy.models import MatchedRule, PolicyEvaluationResult


class PolicyEngine:
    """Evaluate policy decisions using YAML-configured rule sets."""

    def __init__(self, loader: PolicyLoader | None = None) -> None:
        self._loader = loader or PolicyLoader()

    def evaluate(
        self,
        task_type: str,
        tool_id: str,
        resource_type: str,
        resource_id: str,
    ) -> PolicyEvaluationResult:
        bundle = self._loader.load()

        matched: list[MatchedRule] = []
        matched.extend(match_task_rules(task_type=task_type, tool_id=tool_id, rules=bundle.task_tool_rules))
        matched.extend(match_tool_rules(tool_id=tool_id))
        matched.extend(
            match_resource_rules(
                tool_id=tool_id,
                resource_type=resource_type,
                resource_id=resource_id,
                tool_resource_rules=bundle.tool_resource_rules,
                sensitive_rules=bundle.sensitive_resource_rules,
            )
        )

        decision = "allow"
        if any(item.decision == "deny" for item in matched):
            decision = "deny"
        elif any(item.decision == "warn" for item in matched):
            decision = "warn"

        return PolicyEvaluationResult(
            decision=decision,
            matched_rules=matched,
            risk_level=decision_risk_level(decision),
            disposition=decision_to_disposition(decision),
            explanations=render_explanations(matched),
        )


policy_engine = PolicyEngine()
