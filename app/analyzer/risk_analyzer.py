from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models.risk_hit import RiskHit
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

        findings: list[RiskFinding] = []
        task_type = (run.task_type or "unknown").lower()

        workspace_escape = self._detect_workspace_escape(task_type=task_type, events=events)
        if workspace_escape:
            findings.append(workspace_escape)
            logger.info("risk_analyzer.chain_hit run_id=%s chain_id=%s", run_id, workspace_escape.chain_id)

        env_then_http = self._detect_env_then_http(events=events)
        if env_then_http:
            findings.append(env_then_http)
            logger.info("risk_analyzer.chain_hit run_id=%s chain_id=%s", run_id, env_then_http.chain_id)

        analysis_tool = self._detect_analysis_high_risk_tool(task_type=task_type, events=events)
        if analysis_tool:
            findings.append(analysis_tool)
            logger.info("risk_analyzer.chain_hit run_id=%s chain_id=%s", run_id, analysis_tool.chain_id)

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

    def _detect_workspace_escape(self, task_type: str, events: list) -> RiskFinding | None:
        if task_type != "analysis":
            return None

        for event in events:
            if (event.resource_type or "") != "file":
                continue
            resource_id = (event.resource_id or "").strip()
            if not resource_id:
                continue

            if resource_id.startswith("/") or ".." in resource_id:
                return RiskFinding(
                    chain_id="chain_workspace_escape",
                    name="Workspace Boundary Escape",
                    risk_level="high",
                    disposition="deny",
                    reason="Analysis task tried to access a file outside workspace boundary.",
                    event_ids=[event.event_id],
                    path_nodes=[
                        f"task:{event.run_id}",
                        f"tool:{event.tool_id or 'unknown'}",
                        f"resource:file:{resource_id}",
                        f"risk:{event.event_id}",
                    ],
                )
        return None

    def _detect_env_then_http(self, events: list) -> RiskFinding | None:
        env_events = [
            item
            for item in events
            if (item.resource_type or "") == "env"
            and any(keyword in (item.resource_id or "").lower() for keyword in self._sensitive_keywords)
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
                        f"resource:env:{env_event.resource_id or 'unknown'}",
                        f"resource:http:{http_event.resource_id or 'unknown'}",
                        f"risk:{http_event.event_id}",
                    ],
                )

        return None

    def _detect_analysis_high_risk_tool(self, task_type: str, events: list) -> RiskFinding | None:
        if task_type != "analysis":
            return None

        for event in events:
            if event.event_type != "tool_call_requested":
                continue

            tool_id = (event.tool_id or "").lower()
            if not tool_id:
                continue

            if any(keyword in tool_id for keyword in self._high_risk_tool_keywords):
                return RiskFinding(
                    chain_id="chain_analysis_high_risk_tool",
                    name="Analysis Task Triggered High-Risk Tool",
                    risk_level="medium",
                    disposition="warn",
                    reason="Analysis task invoked a high-risk third-party tool.",
                    event_ids=[event.event_id],
                    path_nodes=[
                        f"task:{event.run_id}",
                        f"tool:{event.tool_id}",
                        f"risk:{event.event_id}",
                    ],
                )
        return None

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
