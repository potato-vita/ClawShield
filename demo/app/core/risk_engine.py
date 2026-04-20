from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.models.db_models import EventDB


SEVERITY_WEIGHT = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


class RiskEngine:
    def __init__(self, db: Session, risk_rules_path: str):
        self.db = db
        self.risk_rules_path = Path(risk_rules_path)
        self.rules = self._load_rules()

    def _load_rules(self) -> list[dict]:
        if not self.risk_rules_path.exists():
            return []
        with self.risk_rules_path.open("r", encoding="utf-8") as f:
            payload = yaml.safe_load(f) or {}
        return payload.get("rules", [])

    def evaluate_single_event(self, event: EventDB) -> list[dict]:
        findings: list[dict] = []
        mapping = {
            "workspace_escape": "R1",
            "sensitive": "R2",
            "unauthorized_tool": "R3",
            "domain_not_allowed": "R4",
            "sensitive_env": "R5",
            "dangerous_command": "R6",
        }
        for tag in event.metadata_json.get("tags", []):
            rule_id = mapping.get(tag)
            if not rule_id:
                continue
            rule = self._rule_by_id(rule_id)
            if rule and rule.get("enabled", True):
                findings.append(
                    {
                        "rule_id": rule_id,
                        "name": rule.get("name", rule_id),
                        "severity": rule.get("severity", event.severity),
                        "decision": rule.get("decision", event.decision),
                        "event_id": event.event_id,
                        "message": event.message,
                    }
                )
        return findings

    def evaluate_run_correlations(self, run_id: str) -> list[dict]:
        events = (
            self.db.query(EventDB)
            .filter(EventDB.run_id == run_id)
            .order_by(EventDB.created_at.asc())
            .all()
        )
        findings: list[dict] = []

        r7 = self._rule_by_id("R7")
        if r7 and r7.get("enabled", True):
            window = timedelta(seconds=int(r7.get("time_window_sec", 30)))
            sensitive_events = [
                e
                for e in events
                if e.action.startswith("file_read") and ("sensitive" in e.metadata_json.get("tags", []))
            ]
            http_events = [e for e in events if e.action.startswith("http_request")]

            for src in sensitive_events:
                for dest in http_events:
                    if dest.created_at >= src.created_at and (dest.created_at - src.created_at) <= window:
                        findings.append(
                            {
                                "rule_id": "R7",
                                "name": r7.get("name", "SensitiveReadThenExfiltration"),
                                "severity": r7.get("severity", "critical"),
                                "decision": r7.get("decision", "block"),
                                "event_id": dest.event_id,
                                "message": (
                                    f"Sensitive file read ({src.resource}) followed by outbound request ({dest.resource})"
                                ),
                            }
                        )

        r8 = self._rule_by_id("R8")
        if r8 and r8.get("enabled", True):
            window = timedelta(seconds=int(r8.get("time_window_sec", 30)))
            unauthorized_tool_events = [
                e
                for e in events
                if e.action.startswith("tool_invoke")
                and ("unauthorized_tool" in e.metadata_json.get("tags", []))
            ]
            command_events = [e for e in events if e.action.startswith("command_exec")]

            for src in unauthorized_tool_events:
                for dest in command_events:
                    if dest.created_at >= src.created_at and (dest.created_at - src.created_at) <= window:
                        findings.append(
                            {
                                "rule_id": "R8",
                                "name": r8.get("name", "UnauthorizedToolThenCommand"),
                                "severity": r8.get("severity", "critical"),
                                "decision": r8.get("decision", "block"),
                                "event_id": dest.event_id,
                                "message": (
                                    "Unauthorized tool invocation followed by command execution attempt"
                                ),
                            }
                        )

        r10 = self._rule_by_id("R10")
        if r10 and r10.get("enabled", True):
            window = timedelta(seconds=int(r10.get("time_window_sec", 20)))
            threshold = int(r10.get("threshold", 4))
            probe_events = [
                e
                for e in events
                if e.action.startswith("file_read")
                and (
                    "sensitive" in e.metadata_json.get("tags", [])
                    or "workspace_escape" in e.metadata_json.get("tags", [])
                )
            ]
            for i, start in enumerate(probe_events):
                in_window = [
                    e
                    for e in probe_events[i:]
                    if e.created_at >= start.created_at and (e.created_at - start.created_at) <= window
                ]
                if len(in_window) >= threshold:
                    findings.append(
                        {
                            "rule_id": "R10",
                            "name": r10.get("name", "HighFrequencySensitiveProbe"),
                            "severity": r10.get("severity", "high"),
                            "decision": r10.get("decision", "alert"),
                            "event_id": in_window[-1].event_id,
                            "message": (
                                f"Detected {len(in_window)} sensitive/path-probe reads in "
                                f"{int(window.total_seconds())}s window"
                            ),
                        }
                    )
                    break

        r11 = self._rule_by_id("R11")
        if r11 and r11.get("enabled", True):
            for event in events:
                tags = event.metadata_json.get("tags", [])
                if not event.action.startswith("tool_invoke"):
                    continue
                if "untrusted_skill" in tags and (
                    "unauthorized_tool" in tags or "risky_tool" in tags
                ):
                    findings.append(
                        {
                            "rule_id": "R11",
                            "name": r11.get("name", "UntrustedSkillInvokesHighRiskTool"),
                            "severity": r11.get("severity", "high"),
                            "decision": r11.get("decision", "block"),
                            "event_id": event.event_id,
                            "message": "Untrusted skill attempted high-risk tool invocation",
                        }
                    )

        return findings

    def generate_risk_findings(self, run_id: str) -> dict:
        events = self.db.query(EventDB).filter(EventDB.run_id == run_id).all()
        findings: list[dict] = []
        for event in events:
            findings.extend(self.evaluate_single_event(event))
        findings.extend(self.evaluate_run_correlations(run_id=run_id))

        dedup: dict[str, dict] = {}
        for f in findings:
            key = f"{f['rule_id']}::{f['event_id']}"
            dedup[key] = f
        unique_findings = list(dedup.values())

        max_weight = 1
        for item in unique_findings:
            max_weight = max(max_weight, SEVERITY_WEIGHT.get(item.get("severity", "low"), 1))
        overall = {1: "low", 2: "medium", 3: "high", 4: "critical"}.get(max_weight, "low")

        return {
            "overall_risk_level": overall,
            "findings": unique_findings,
        }

    def _rule_by_id(self, rule_id: str) -> dict | None:
        for rule in self.rules:
            if rule.get("rule_id") == rule_id:
                return rule
        return None
