from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models.risk_hit import RiskHit
from app.policy.loader import PolicyLoader
from app.policy.models import RiskChainRule
from app.repositories.risk_repo import risk_repository
from app.repositories.run_repo import run_repository
from app.schemas.evidence import RiskFinding
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)


class RiskAnalyzer:
    """Detect multi-event risk chains and produce final run-level findings."""

    _sensitive_keywords = ("key", "token", "secret", "password", "credential")
    _high_risk_tool_keywords = ("shell", "exec", "plugin", "delete", "system", "danger")
    _env_to_http_window = timedelta(minutes=10)

    def __init__(self) -> None:
        self._policy_loader = PolicyLoader()

    def analyze(self, db: Session, run_id: str) -> dict[str, object]:
        run = run_repository.get_by_run_id(db=db, run_id=run_id)
        if run is None:
            logger.warning("risk_analyzer.run_not_found run_id=%s", run_id)
            return {
                "findings": [],
                "final_risk_level": None,
                "final_disposition": "allow",
                "summary": "run not found",
            }

        events = audit_service.list_events(
            db=db,
            run_id=run_id,
            limit=1000,
            offset=0,
            order="asc",
        )
        task_type = (run.task_type or "unknown").lower()

        findings, used_config = self._detect_from_rules(task_type=task_type, events=events)
        if not used_config:
            findings = self._legacy_detect(task_type=task_type, events=events)

        for item in findings:
            logger.info("risk_analyzer.chain_hit run_id=%s chain_id=%s", run_id, item.chain_id)

        final_risk_level = self._max_risk([item.risk_level for item in findings])
        final_disposition = "deny" if any(item.disposition == "deny" for item in findings) else "warn"
        if not findings:
            final_disposition = "allow"

        persisted = [
            RiskHit(
                run_id=run_id,
                rule_id=item.chain_id,
                rule_type="risk_chain",
                risk_level=item.risk_level,
                explanation=item.reason,
            )
            for item in findings
        ]
        risk_repository.replace_for_run(db=db, run_id=run_id, findings=persisted)
        logger.info(
            "risk_analyzer.done run_id=%s finding_count=%s final_risk_level=%s final_disposition=%s",
            run_id,
            len(findings),
            final_risk_level,
            final_disposition,
        )

        return {
            "findings": findings,
            "final_risk_level": final_risk_level,
            "final_disposition": final_disposition,
            "summary": self._build_summary(findings=findings, final_risk_level=final_risk_level),
        }

    def _detect_from_rules(self, task_type: str, events: list) -> tuple[list[RiskFinding], bool]:
        try:
            bundle = self._policy_loader.load()
            rules = [rule for rule in bundle.risk_chain_rules if rule.enabled and rule.chain_id]
        except Exception as exc:
            logger.warning("risk_analyzer.rule_load_failed: %s", exc)
            return [], False

        if not rules:
            return [], False

        findings: list[RiskFinding] = []
        for rule in rules:
            matched_events = self._match_rule_sequence(rule=rule, task_type=task_type, events=events)
            if not matched_events:
                continue
            finding = self._build_finding_from_rule(rule=rule, matched_events=matched_events)
            if finding is not None:
                findings.append(finding)
        return findings, True

    def _match_rule_sequence(self, rule: RiskChainRule, task_type: str, events: list) -> list | None:
        if rule.task_types and task_type not in {item.lower() for item in rule.task_types}:
            return None

        sequence = [item for item in rule.sequence if isinstance(item, dict)]
        if not sequence:
            return None

        window = timedelta(seconds=max(rule.window_seconds, 0))
        for start_index, event in enumerate(events):
            if not self._event_matches(event=event, condition=sequence[0]):
                continue

            matched = [event]
            first_ts = event.ts
            cursor = start_index + 1
            success = True
            for step_condition in sequence[1:]:
                hit = None
                while cursor < len(events):
                    candidate = events[cursor]
                    cursor += 1
                    if window.total_seconds() > 0 and (candidate.ts - first_ts) > window:
                        break
                    if self._event_matches(event=candidate, condition=step_condition):
                        hit = candidate
                        break
                if hit is None:
                    success = False
                    break
                matched.append(hit)

            if success:
                return matched
        return None

    def _event_matches(self, event, condition: dict[str, Any]) -> bool:
        event_type = (event.event_type or "").lower()
        resource_type = (event.resource_type or "").lower()
        resource_id = (event.resource_id or "")
        tool_id = (event.tool_id or "").lower()
        alignment_decision = (event.alignment_decision or "").lower()
        disposition = (event.disposition or "").lower()
        risk_level = (event.risk_level or "").lower()
        status = (event.status or "").lower()
        event_stage = (event.event_stage or "").lower()

        expected_type = str(condition.get("event_type", "")).lower()
        if expected_type and event_type != expected_type:
            return False

        expected_types = condition.get("event_type_in", [])
        if isinstance(expected_types, list) and expected_types:
            normalized = {str(item).lower() for item in expected_types}
            if event_type not in normalized:
                return False

        expected_resource = str(condition.get("resource_type", "")).lower()
        if expected_resource and resource_type != expected_resource:
            return False

        expected_alignment = str(condition.get("alignment_decision", "")).lower()
        if expected_alignment and alignment_decision != expected_alignment:
            return False

        expected_disposition = str(condition.get("disposition", "")).lower()
        if expected_disposition and disposition != expected_disposition:
            return False

        expected_risk = str(condition.get("risk_level", "")).lower()
        if expected_risk and risk_level != expected_risk:
            return False

        expected_risks = condition.get("risk_level_in", [])
        if isinstance(expected_risks, list) and expected_risks:
            normalized = {str(item).lower() for item in expected_risks}
            if risk_level not in normalized:
                return False

        expected_status = str(condition.get("status", "")).lower()
        if expected_status and status != expected_status:
            return False

        expected_stage = str(condition.get("event_stage", "")).lower()
        if expected_stage and event_stage != expected_stage:
            return False

        tool_contains = str(condition.get("tool_id_contains", "")).lower()
        if tool_contains and tool_contains not in tool_id:
            return False

        tool_contains_any = condition.get("tool_id_contains_any", [])
        if isinstance(tool_contains_any, list) and tool_contains_any:
            normalized = [str(item).lower() for item in tool_contains_any]
            if not any(item in tool_id for item in normalized):
                return False

        resource_contains = str(condition.get("resource_id_contains", ""))
        if resource_contains and resource_contains not in resource_id:
            return False

        resource_contains_any = condition.get("resource_id_contains_any", [])
        if isinstance(resource_contains_any, list) and resource_contains_any:
            normalized = [str(item) for item in resource_contains_any]
            if not any(item in resource_id for item in normalized):
                return False

        resource_prefix_any = condition.get("resource_id_prefix_any", [])
        if isinstance(resource_prefix_any, list) and resource_prefix_any:
            normalized = [str(item) for item in resource_prefix_any]
            if not any(resource_id.startswith(item) for item in normalized):
                return False

        if bool(condition.get("sensitive_env")) and not self._is_sensitive_env(resource_id=resource_id):
            return False

        if bool(condition.get("workspace_escape")) and not self._is_workspace_escape(resource_id=resource_id):
            return False

        if bool(condition.get("high_risk_tool")) and not self._is_high_risk_tool(tool_id=tool_id):
            return False

        return True

    def _build_finding_from_rule(self, rule: RiskChainRule, matched_events: list) -> RiskFinding | None:
        if not matched_events:
            return None

        chain_id = rule.chain_id
        name = rule.name or self._humanize_chain_id(chain_id)
        reason = rule.explain or f"risk chain matched: {chain_id}"
        risk_level = (rule.risk_level or "medium").lower()
        disposition = (rule.disposition or "warn").lower()
        event_ids = [item.event_id for item in matched_events if item.event_id]
        path_nodes = self._build_path_nodes(matched_events=matched_events)

        return RiskFinding(
            chain_id=chain_id,
            name=name,
            risk_level=risk_level,
            disposition=disposition,
            reason=reason,
            event_ids=event_ids,
            path_nodes=path_nodes,
        )

    @staticmethod
    def _build_path_nodes(matched_events: list) -> list[str]:
        if not matched_events:
            return []
        run_id = matched_events[0].run_id
        nodes: list[str] = [f"task:{run_id}", f"goal:{run_id}"]
        for event in matched_events:
            if event.step_id:
                nodes.append(f"step:{event.step_id}")
            if event.tool_call_id:
                nodes.append(f"intent:{event.tool_call_id}")
            if event.tool_id:
                nodes.append(f"tool:{event.tool_id}")
            if event.resource_type or event.resource_id:
                nodes.append(f"resource:{event.resource_type or 'unknown'}:{event.resource_id or 'unknown'}")
            if event.impact_level or event.intended_effect:
                nodes.append(f"impact:{event.event_id}")
            if event.alignment_decision:
                nodes.append(f"alignment:{event.event_id}")
            if event.disposition:
                nodes.append(f"disposition:{event.event_id}")
        nodes.append(f"risk:{matched_events[-1].event_id}")
        deduped: list[str] = []
        seen: set[str] = set()
        for node in nodes:
            if node in seen:
                continue
            seen.add(node)
            deduped.append(node)
        return deduped

    def _legacy_detect(self, task_type: str, events: list) -> list[RiskFinding]:
        findings: list[RiskFinding] = []

        workspace_escape = self._legacy_detect_workspace_escape(task_type=task_type, events=events)
        if workspace_escape:
            findings.append(workspace_escape)

        env_then_http = self._legacy_detect_env_then_http(events=events)
        if env_then_http:
            findings.append(env_then_http)

        analysis_tool = self._legacy_detect_analysis_high_risk_tool(task_type=task_type, events=events)
        if analysis_tool:
            findings.append(analysis_tool)

        alignment_mismatch = self._legacy_detect_goal_mismatch(events=events)
        if alignment_mismatch:
            findings.append(alignment_mismatch)

        return findings

    def _legacy_detect_workspace_escape(self, task_type: str, events: list) -> RiskFinding | None:
        if task_type != "analysis":
            return None
        for event in events:
            if (event.resource_type or "") != "file":
                continue
            if not self._is_workspace_escape(event.resource_id or ""):
                continue
            resource_id = event.resource_id or "unknown"
            return RiskFinding(
                chain_id="chain_workspace_escape",
                name="Workspace Boundary Escape",
                risk_level="high",
                disposition="deny",
                reason="Analysis task tried to access a file outside workspace boundary.",
                event_ids=[event.event_id],
                path_nodes=[
                    f"task:{event.run_id}",
                    f"goal:{event.run_id}",
                    f"tool:{event.tool_id or 'unknown'}",
                    f"resource:file:{resource_id}",
                    f"risk:{event.event_id}",
                ],
            )
        return None

    def _legacy_detect_env_then_http(self, events: list) -> RiskFinding | None:
        env_events = [
            item
            for item in events
            if (item.resource_type or "") == "env"
            and self._is_sensitive_env(item.resource_id or "")
        ]
        if not env_events:
            return None
        http_events = [item for item in events if (item.resource_type or "") == "http"]
        if not http_events:
            return None
        for env_event in env_events:
            for http_event in http_events:
                if http_event.ts < env_event.ts:
                    continue
                if (http_event.ts - env_event.ts) > self._env_to_http_window:
                    continue
                return RiskFinding(
                    chain_id="chain_env_then_http",
                    name="Sensitive Env Read Followed By External Request",
                    risk_level="high",
                    disposition="deny",
                    reason="Sensitive environment variable was read before an external HTTP request.",
                    event_ids=[env_event.event_id, http_event.event_id],
                    path_nodes=[
                        f"task:{env_event.run_id}",
                        f"goal:{env_event.run_id}",
                        f"resource:env:{env_event.resource_id or 'unknown'}",
                        f"resource:http:{http_event.resource_id or 'unknown'}",
                        f"risk:{http_event.event_id}",
                    ],
                )
        return None

    def _legacy_detect_analysis_high_risk_tool(self, task_type: str, events: list) -> RiskFinding | None:
        if task_type != "analysis":
            return None
        for event in events:
            if event.event_type != "tool_call_requested":
                continue
            if not self._is_high_risk_tool(event.tool_id or ""):
                continue
            return RiskFinding(
                chain_id="chain_analysis_high_risk_tool",
                name="Analysis Task Triggered High-Risk Tool",
                risk_level="medium",
                disposition="warn",
                reason="Analysis task invoked a high-risk third-party tool.",
                event_ids=[event.event_id],
                path_nodes=[
                    f"task:{event.run_id}",
                    f"goal:{event.run_id}",
                    f"tool:{event.tool_id}",
                    f"risk:{event.event_id}",
                ],
            )
        return None

    def _legacy_detect_goal_mismatch(self, events: list) -> RiskFinding | None:
        for event in events:
            if event.event_type in {"alignment_blocked", "alignment_evaluation_completed"} and event.alignment_decision == "deny":
                return RiskFinding(
                    chain_id="goal_mismatch_tool_call",
                    name="Goal Mismatch Tool Call",
                    risk_level=event.risk_level or "high",
                    disposition="deny",
                    reason="Tool call is not aligned with the declared task goal and step context.",
                    event_ids=[event.event_id],
                    path_nodes=[
                        f"task:{event.run_id}",
                        f"goal:{event.run_id}",
                        f"step:{event.step_id or 'unknown'}",
                        f"tool:{event.tool_id or 'unknown'}",
                        f"alignment:{event.event_id}",
                        f"risk:{event.event_id}",
                    ],
                )
        return None

    @staticmethod
    def _is_workspace_escape(resource_id: str) -> bool:
        normalized = resource_id.strip()
        if not normalized:
            return False
        return normalized.startswith("/") or ".." in normalized

    def _is_sensitive_env(self, resource_id: str) -> bool:
        lowered = resource_id.lower()
        return any(keyword in lowered for keyword in self._sensitive_keywords)

    def _is_high_risk_tool(self, tool_id: str) -> bool:
        lowered = tool_id.lower()
        return any(keyword in lowered for keyword in self._high_risk_tool_keywords)

    @staticmethod
    def _humanize_chain_id(chain_id: str) -> str:
        return chain_id.replace("_", " ").replace("-", " ").title()

    @staticmethod
    def _max_risk(levels: list[str]) -> str | None:
        if not levels:
            return None

        rank = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4,
            "severe": 4,
        }
        winner = "low"
        winner_rank = 0
        for level in levels:
            normalized = (level or "low").lower()
            current_rank = rank.get(normalized, 0)
            if current_rank > winner_rank:
                winner = normalized
                winner_rank = current_rank
        return winner if winner_rank > 0 else None

    @staticmethod
    def _build_summary(findings: list[RiskFinding], final_risk_level: str | None) -> str:
        if not findings:
            return "No chained risk findings were detected."

        chain_names = ", ".join(item.name for item in findings)
        return (
            f"Detected {len(findings)} chained finding(s): {chain_names}. "
            f"Final risk level: {final_risk_level or 'unknown'}."
        )


risk_analyzer = RiskAnalyzer()
