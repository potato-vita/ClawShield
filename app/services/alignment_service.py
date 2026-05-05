from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.core.ids import generate_eval_id
from app.models.alignment_evaluation import AlignmentEvaluation
from app.models.task_goal import TaskGoal
from app.models.task_step import TaskStep
from app.repositories.alignment_repo import AlignmentRepository, alignment_repository
from app.schemas.alignment import AlignmentEvaluationData
from app.schemas.impact import ResourceImpact
from app.schemas.intent import ToolCallIntent

PROJECT_ROOT = Path(__file__).resolve().parents[2]
THRESHOLDS_PATH = PROJECT_ROOT / "configs" / "rules" / "alignment_thresholds.yaml"
EFFECT_RULES_PATH = PROJECT_ROOT / "configs" / "rules" / "effect_rules.yaml"


class AlignmentService:
    def __init__(self, repository: AlignmentRepository) -> None:
        self._repository = repository

    def evaluate(
        self,
        db: Session,
        goal: TaskGoal | None,
        step: TaskStep | None,
        intent: ToolCallIntent,
        impact: ResourceImpact,
        model_reason: str | None,
        justification_ref: str | None = None,
        counterfactual_note: str | None = None,
        enforce_justification: bool = False,
    ) -> AlignmentEvaluationData:
        thresholds = self._load_yaml(THRESHOLDS_PATH)
        effect_rules = self._load_yaml(EFFECT_RULES_PATH)
        reasons: list[str] = []
        matched_rules: list[dict[str, Any]] = []
        hard_reason_codes: list[str] = []
        task_intent = goal.task_intent if goal else "unknown"
        profile = self._resolve_threshold_profile(thresholds=thresholds, task_intent=task_intent)
        weights = profile["weights"]
        threshold_values = profile["thresholds"]
        penalty_values = profile["penalties"]

        self._evaluate_hard_constraints(
            goal=goal,
            step=step,
            intent=intent,
            impact=impact,
            hard_reason_codes=hard_reason_codes,
            matched_rules=matched_rules,
            reasons=reasons,
        )

        goal_relevance = self._goal_relevance(goal=goal, intent=intent, reasons=reasons)
        state_legality = self._state_legality(step=step, intent=intent, reasons=reasons)
        resource_necessity = self._resource_necessity(goal=goal, impact=impact, reasons=reasons)
        effect_safety = self._effect_safety(impact=impact, reasons=reasons)
        reason_support = self._reason_support(model_reason=model_reason, intent=intent, reasons=reasons)
        necessity_verdict = self._necessity_verdict(resource_necessity=resource_necessity)
        anomaly_penalty, exfiltration_penalty, penalty_reasons = self._compute_penalties(
            impact=impact,
            reason_support=reason_support,
            penalty_values=penalty_values,
        )
        reasons.extend(penalty_reasons)

        redline_hit, redline_rules = self._check_redlines(goal=goal, impact=impact, rules=effect_rules)
        if redline_hit:
            matched_rules.extend(redline_rules)
            reasons.extend([item.get("reason", "redline_hit") for item in redline_rules])
            hard_reason_codes.append("hard_redline_rule")

        weighted_score = (
            goal_relevance * float(weights.get("goal_relevance", 0.28))
            + state_legality * float(weights.get("state_legality", 0.2))
            + resource_necessity * float(weights.get("resource_necessity", 0.18))
            + effect_safety * float(weights.get("effect_safety", 0.22))
            + reason_support * float(weights.get("reason_support", 0.12))
        )
        overall_score = self._clamp_score(weighted_score - anomaly_penalty - exfiltration_penalty)
        allow_threshold = float(threshold_values.get("allow", 0.8))
        review_threshold = float(threshold_values.get("review", 0.55))

        if hard_reason_codes:
            decision = "deny"
        elif redline_hit:
            decision = "deny"
        elif overall_score >= allow_threshold and necessity_verdict == "necessary":
            decision = "allow"
        elif overall_score >= review_threshold:
            decision = "review"
        else:
            decision = "deny"

        if decision == "review":
            reasons.append("review_score_or_necessity_triggered")
            if necessity_verdict != "necessary":
                reasons.append(f"review_necessity_{necessity_verdict}")
        if decision == "deny" and (not hard_reason_codes) and (not redline_hit):
            reasons.append("deny_score_below_review_threshold")

        if enforce_justification and not justification_ref and decision != "deny":
            decision = "review"
            reasons.append("causal_justification_missing_force_review")

        risk_level = str(thresholds.get("risk_by_decision", {}).get(decision, "medium"))
        score_breakdown = {
            "goal_relevance": goal_relevance,
            "state_legality": state_legality,
            "resource_necessity": resource_necessity,
            "effect_safety": effect_safety,
            "reason_support": reason_support,
            "weighted_score": weighted_score,
            "anomaly_penalty": anomaly_penalty,
            "exfiltration_penalty": exfiltration_penalty,
            "final_score": overall_score,
            "allow_threshold": allow_threshold,
            "review_threshold": review_threshold,
            "justification_present": 1.0 if bool(justification_ref) else 0.0,
        }
        matched_rules_with_breakdown = [
            *matched_rules,
            {
                "rule_id": "score_breakdown_v2",
                "reason": "alignment_score_breakdown_persisted",
                "details": score_breakdown,
                "necessity_verdict": necessity_verdict,
            },
            {
                "rule_id": "causal_verification_v1",
                "reason": "goal_step_justification_reference",
                "justification_ref": justification_ref,
                "counterfactual_note": counterfactual_note,
            },
        ]

        row = AlignmentEvaluation(
            eval_id=generate_eval_id(),
            run_id=intent.run_id,
            tool_call_id=intent.tool_call_id,
            goal_id=goal.goal_id if goal else None,
            step_id=step.step_id if step else intent.step_id,
            goal_relevance=goal_relevance,
            state_legality=state_legality,
            resource_necessity=resource_necessity,
            effect_safety=effect_safety,
            reason_support=reason_support,
            overall_score=overall_score,
            decision=decision,
            risk_level=risk_level,
            reasons_json=self._dedupe_str_list([*hard_reason_codes, *reasons]),
            matched_rules_json=matched_rules_with_breakdown,
        )
        persisted = self._repository.create(db=db, evaluation=row)
        return AlignmentEvaluationData(
            eval_id=persisted.eval_id,
            run_id=persisted.run_id,
            tool_call_id=persisted.tool_call_id,
            goal_id=persisted.goal_id,
            step_id=persisted.step_id,
            goal_relevance=persisted.goal_relevance,
            state_legality=persisted.state_legality,
            resource_necessity=persisted.resource_necessity,
            effect_safety=persisted.effect_safety,
            reason_support=persisted.reason_support,
            anomaly_penalty=anomaly_penalty,
            exfiltration_penalty=exfiltration_penalty,
            necessity_verdict=necessity_verdict,
            score_breakdown=score_breakdown,
            justification_ref=justification_ref,
            counterfactual_note=counterfactual_note,
            overall_score=persisted.overall_score,
            decision=persisted.decision,
            risk_level=persisted.risk_level,
            reasons=list(persisted.reasons_json),
            matched_rules=list(persisted.matched_rules_json),
            hard_reason_codes=list(hard_reason_codes),
            created_at=persisted.created_at,
        )

    @staticmethod
    def _resolve_threshold_profile(thresholds: dict[str, Any], task_intent: str) -> dict[str, dict[str, float]]:
        default_weights = thresholds.get("weights", {})
        default_thresholds = thresholds.get("thresholds", {})
        default_penalties = thresholds.get("penalties", {})
        profiles = thresholds.get("task_intent_profiles", {})
        profile = profiles.get(task_intent, {}) if isinstance(profiles, dict) else {}

        profile_weights = profile.get("weights", {}) if isinstance(profile, dict) else {}
        profile_thresholds = profile.get("thresholds", {}) if isinstance(profile, dict) else {}

        return {
            "weights": {
                "goal_relevance": float(profile_weights.get("goal_relevance", default_weights.get("goal_relevance", 0.28))),
                "state_legality": float(profile_weights.get("state_legality", default_weights.get("state_legality", 0.2))),
                "resource_necessity": float(profile_weights.get("resource_necessity", default_weights.get("resource_necessity", 0.18))),
                "effect_safety": float(profile_weights.get("effect_safety", default_weights.get("effect_safety", 0.22))),
                "reason_support": float(profile_weights.get("reason_support", default_weights.get("reason_support", 0.12))),
            },
            "thresholds": {
                "allow": float(profile_thresholds.get("allow", default_thresholds.get("allow", 0.8))),
                "review": float(profile_thresholds.get("review", default_thresholds.get("review", 0.55))),
            },
            "penalties": {
                "untrusted_domain": float(default_penalties.get("untrusted_domain", 0.08)),
                "workspace_scope_violation": float(default_penalties.get("workspace_scope_violation", 0.08)),
                "weak_justification": float(default_penalties.get("weak_justification", 0.05)),
                "exfiltration_risk": float(default_penalties.get("exfiltration_risk", 0.2)),
                "multi_stage_exfiltration": float(default_penalties.get("multi_stage_exfiltration", 0.12)),
            },
        }

    @staticmethod
    def _compute_penalties(
        impact: ResourceImpact,
        reason_support: float,
        penalty_values: dict[str, float],
    ) -> tuple[float, float, list[str]]:
        reasons: list[str] = []
        anomaly_penalty = 0.0
        exfiltration_penalty = 0.0

        if (impact.domain_trust_level or "") == "untrusted":
            anomaly_penalty += float(penalty_values.get("untrusted_domain", 0.08))
            reasons.append("penalty_untrusted_domain")

        if "workspace_scope_violation" in impact.impact_signals:
            anomaly_penalty += float(penalty_values.get("workspace_scope_violation", 0.08))
            reasons.append("penalty_workspace_scope_violation")

        if reason_support < 0.55:
            anomaly_penalty += float(penalty_values.get("weak_justification", 0.05))
            reasons.append("penalty_weak_justification")

        if impact.exfiltration_risk:
            exfiltration_penalty += float(penalty_values.get("exfiltration_risk", 0.2))
            reasons.append("penalty_exfiltration_risk")

        if "multi_stage_exfiltration_pattern" in impact.impact_signals:
            exfiltration_penalty += float(penalty_values.get("multi_stage_exfiltration", 0.12))
            reasons.append("penalty_multi_stage_exfiltration")

        anomaly_penalty = min(anomaly_penalty, 0.3)
        exfiltration_penalty = min(exfiltration_penalty, 0.45)
        return anomaly_penalty, exfiltration_penalty, reasons

    @staticmethod
    def _necessity_verdict(resource_necessity: float) -> str:
        if resource_necessity >= 0.8:
            return "necessary"
        if resource_necessity >= 0.5:
            return "weakly_necessary"
        return "unnecessary"

    @staticmethod
    def _clamp_score(score: float) -> float:
        return max(0.0, min(1.0, score))

    @classmethod
    def _evaluate_hard_constraints(
        cls,
        goal: TaskGoal | None,
        step: TaskStep | None,
        intent: ToolCallIntent,
        impact: ResourceImpact,
        hard_reason_codes: list[str],
        matched_rules: list[dict[str, Any]],
        reasons: list[str],
    ) -> None:
        if goal is None:
            if intent.action_type in {"http", "env_read"}:
                hard_reason_codes.append("hard_unknown_goal_high_risk_action")
                reasons.append("goal_missing_for_high_risk_action")
            return

        forbidden_actions = set(goal.forbidden_actions_json or [])
        forbidden_effects = set(goal.forbidden_effects_json or [])
        unknown_intent = goal.task_intent == "unknown"

        if intent.action_type in forbidden_actions:
            hard_reason_codes.append("hard_forbidden_action")
            matched_rules.append(
                {
                    "rule_id": "goal_forbidden_action",
                    "reason": f"goal_forbids_action:{intent.action_type}",
                }
            )

        if (impact.effect_type in forbidden_effects) and (not unknown_intent):
            hard_reason_codes.append("hard_forbidden_effect")
            matched_rules.append(
                {
                    "rule_id": "goal_forbidden_effect",
                    "reason": f"goal_forbids_effect:{impact.effect_type}",
                }
            )

        if impact.resource_type == "env":
            # Keep env read as a strong risk factor for scoring/redline handling,
            # but do not always hard-block here to preserve runtime chain visibility.
            reasons.append("env_access_requires_explicit_review")

        if (
            impact.resource_type == "http"
            and impact.effect_type == "upload"
            and (impact.domain_trust_level or "") == "untrusted"
        ):
            if goal is None or goal.task_intent not in {"external_invoke", "admin_op"}:
                hard_reason_codes.append("hard_untrusted_upload")
                matched_rules.append(
                    {
                        "rule_id": "untrusted_http_upload_block",
                        "reason": "untrusted_domain_upload_not_allowed",
                    }
                )

        if cls._resource_out_of_scope(goal=goal, impact=impact):
            hard_reason_codes.append("hard_resource_scope_violation")
            matched_rules.append(
                {
                    "rule_id": "goal_resource_scope_violation",
                    "reason": f"resource_out_of_scope:{impact.resource_type}:{impact.resource_id}",
                }
            )

        if step is not None and intent.action_type not in (step.allowed_action_types_json or []):
            hard_reason_codes.append("hard_state_action_violation")
            matched_rules.append(
                {
                    "rule_id": "state_action_not_allowed",
                    "reason": f"state={step.state}; action={intent.action_type}",
                }
            )

    @staticmethod
    def _resource_out_of_scope(goal: TaskGoal, impact: ResourceImpact) -> bool:
        if goal.task_intent == "unknown":
            # Unknown intent should still be conservative via score/redline,
            # but keep runtime observability for env/http flows.
            return False
        scopes = [str(item) for item in (goal.allowed_resource_scopes_json or [])]
        if not scopes:
            return True

        if impact.resource_type == "file":
            resource_id = (impact.resource_id or "").strip()
            if not resource_id:
                return True
            if resource_id.startswith("/"):
                return True
            if ".." in resource_id:
                return True
            return not any(scope.startswith("workspace/") or scope.startswith("repo/") for scope in scopes)

        if impact.resource_type == "http":
            resource = (impact.resource_id or "").strip().lower()
            if not resource:
                return True
            if not resource.startswith("http://") and not resource.startswith("https://"):
                return True
            http_scopes = [
                str(scope).strip().lower()
                for scope in scopes
                if str(scope).strip().lower().startswith("http://") or str(scope).strip().lower().startswith("https://")
            ]
            if not http_scopes:
                return True
            if any(scope.endswith("*") and resource.startswith(scope[:-1]) for scope in http_scopes):
                return False
            if any(resource.startswith(scope) for scope in http_scopes):
                return False
            return True

        if impact.resource_type == "env":
            return True

        return False

    @staticmethod
    def _goal_relevance(goal: TaskGoal | None, intent: ToolCallIntent, reasons: list[str]) -> float:
        if goal is None:
            reasons.append("goal_missing")
            return 0.4
        if intent.action_type in goal.allowed_action_types_json:
            return 0.95
        reasons.append("action_not_in_goal_allowset")
        return 0.25

    @staticmethod
    def _state_legality(step: TaskStep | None, intent: ToolCallIntent, reasons: list[str]) -> float:
        if step is None:
            reasons.append("step_missing")
            return 0.45
        if intent.action_type in step.allowed_action_types_json:
            return 0.9
        reasons.append("action_not_allowed_in_step")
        return 0.2

    @staticmethod
    def _resource_necessity(goal: TaskGoal | None, impact: ResourceImpact, reasons: list[str]) -> float:
        if goal is None:
            return 0.5
        scopes = goal.allowed_resource_scopes_json
        if impact.resource_type == "file":
            if any(scope.startswith("workspace/") or scope.startswith("workspace/**") for scope in scopes):
                return 0.9
        if impact.resource_type == "http":
            if any(scope.startswith("http") for scope in scopes):
                return 0.8
            reasons.append("http_not_required_for_goal")
            return 0.2
        if impact.resource_type == "env":
            reasons.append("env_access_not_necessary")
            return 0.2
        return 0.6

    @staticmethod
    def _effect_safety(impact: ResourceImpact, reasons: list[str]) -> float:
        mapping = {"low": 0.95, "medium": 0.65, "high": 0.3, "critical": 0.05}
        score = mapping.get(impact.impact_level, 0.5)
        if impact.exfiltration_risk:
            reasons.append("exfiltration_risk_detected")
            score = min(score, 0.2)
        if impact.mutation_risk:
            reasons.append("mutation_risk_detected")
            score = min(score, 0.35)
        return score

    @staticmethod
    def _reason_support(model_reason: str | None, intent: ToolCallIntent, reasons: list[str]) -> float:
        if not model_reason:
            reasons.append("model_reason_missing")
            return 0.3
        text = model_reason.lower()
        if intent.action_type in {"file_read", "env_read"} and "read" in text:
            return 0.9
        if intent.action_type == "http" and ("http" in text or "request" in text or "api" in text):
            return 0.85
        reasons.append("model_reason_weak")
        return 0.5

    @staticmethod
    def _check_redlines(goal: TaskGoal | None, impact: ResourceImpact, rules: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
        redlines = rules.get("redlines", [])
        if not isinstance(redlines, list):
            return False, []
        hits: list[dict[str, Any]] = []
        task_intent = goal.task_intent if goal else "unknown"
        for rule in redlines:
            if not isinstance(rule, dict):
                continue
            allowed_intents = rule.get("task_intents", [])
            if allowed_intents and task_intent not in allowed_intents:
                continue
            effect_types = rule.get("effect_types", [])
            impact_levels = rule.get("impact_levels", [])
            condition = str(rule.get("condition", ""))
            effect_ok = (not effect_types) or (impact.effect_type in effect_types)
            impact_ok = (not impact_levels) or (impact.impact_level in impact_levels)
            condition_ok = True
            if condition == "exfiltration_risk":
                condition_ok = impact.exfiltration_risk
            if effect_ok and impact_ok and condition_ok:
                hits.append(
                    {
                        "rule_id": rule.get("id", "redline"),
                        "reason": rule.get("reason", "redline_hit"),
                    }
                )
        return (len(hits) > 0), hits

    @staticmethod
    def _dedupe_str_list(values: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            deduped.append(value)
        return deduped

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        if not isinstance(loaded, dict):
            return {}
        return loaded


alignment_service = AlignmentService(repository=alignment_repository)
