from datetime import timedelta

from app.core.risk_engine import RiskEngine
from app.models.db_models import EventDB
from app.utils.time import utc_now


def test_r7_sensitive_then_exfiltration_detected(db_session, tmp_path):
    risk_rules = tmp_path / "risk_rules.yaml"
    risk_rules.write_text(
        """
rules:
  - rule_id: R7
    name: SensitiveReadThenExfiltration
    category: correlation
    severity: critical
    decision: block
    enabled: true
    time_window_sec: 30
""".strip(),
        encoding="utf-8",
    )

    t0 = utc_now()
    e1 = EventDB(
        event_id="evt_a",
        run_id="run_risk_1",
        task_id="task",
        parent_event_id=None,
        event_type="action_completed",
        action="file_read",
        resource_type="file",
        resource=".env",
        params_summary="",
        decision="alert",
        result_status="ok",
        severity="medium",
        message="sensitive read",
        created_at=t0,
        trace_id=None,
        metadata_json={"tags": ["sensitive"], "sensitive": True},
    )
    e2 = EventDB(
        event_id="evt_b",
        run_id="run_risk_1",
        task_id="task",
        parent_event_id=None,
        event_type="action_blocked",
        action="http_request",
        resource_type="url",
        resource="https://evil.example/upload",
        params_summary="",
        decision="block",
        result_status="blocked",
        severity="high",
        message="domain blocked",
        created_at=t0 + timedelta(seconds=6),
        trace_id=None,
        metadata_json={"tags": ["domain_not_allowed"]},
    )
    db_session.add(e1)
    db_session.add(e2)
    db_session.commit()

    engine = RiskEngine(db=db_session, risk_rules_path=str(risk_rules))
    result = engine.generate_risk_findings("run_risk_1")

    rule_ids = {x["rule_id"] for x in result["findings"]}
    assert "R7" in rule_ids
    assert result["overall_risk_level"] in {"high", "critical"}


def test_r8_r10_r11_detected_for_complex_chain(db_session, tmp_path):
    risk_rules = tmp_path / "risk_rules.yaml"
    risk_rules.write_text(
        """
rules:
  - rule_id: R8
    name: UnauthorizedToolThenCommand
    category: correlation
    severity: critical
    decision: block
    enabled: true
    time_window_sec: 30
  - rule_id: R10
    name: HighFrequencySensitiveProbe
    category: correlation
    severity: high
    decision: alert
    enabled: true
    time_window_sec: 20
    threshold: 4
  - rule_id: R11
    name: UntrustedSkillInvokesHighRiskTool
    category: trust
    severity: high
    decision: block
    enabled: true
""".strip(),
        encoding="utf-8",
    )

    t0 = utc_now()
    probe_tags = {"tags": ["sensitive"]}
    for idx in range(4):
        db_session.add(
            EventDB(
                event_id=f"evt_probe_{idx}",
                run_id="run_risk_2",
                task_id="task",
                parent_event_id=None,
                event_type="file_read_attempt",
                action="file_read",
                resource_type="file",
                resource=f"secret_{idx}.txt",
                params_summary="",
                decision="alert",
                result_status="ok",
                severity="medium",
                message="probe",
                created_at=t0 + timedelta(seconds=idx),
                trace_id=None,
                metadata_json=probe_tags,
            )
        )

    db_session.add(
        EventDB(
            event_id="evt_tool_bad",
            run_id="run_risk_2",
            task_id="task",
            parent_event_id=None,
            event_type="tool_invoke_attempt",
            action="tool_invoke",
            resource_type="tool",
            resource="data_exporter",
            params_summary="",
            decision="block",
            result_status="blocked",
            severity="high",
            message="unauthorized tool",
            created_at=t0 + timedelta(seconds=6),
            trace_id=None,
            metadata_json={"tags": ["unauthorized_tool", "untrusted_skill"]},
        )
    )
    db_session.add(
        EventDB(
            event_id="evt_cmd_bad",
            run_id="run_risk_2",
            task_id="task",
            parent_event_id=None,
            event_type="command_exec_attempt",
            action="command_exec",
            resource_type="command",
            resource="rm -rf /",
            params_summary="",
            decision="block",
            result_status="blocked",
            severity="critical",
            message="dangerous command",
            created_at=t0 + timedelta(seconds=8),
            trace_id=None,
            metadata_json={"tags": ["dangerous_command"]},
        )
    )
    db_session.commit()

    engine = RiskEngine(db=db_session, risk_rules_path=str(risk_rules))
    result = engine.generate_risk_findings("run_risk_2")
    rule_ids = {x["rule_id"] for x in result["findings"]}

    assert "R8" in rule_ids
    assert "R10" in rule_ids
    assert "R11" in rule_ids
    assert result["overall_risk_level"] == "critical"
