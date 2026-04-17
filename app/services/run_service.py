from sqlalchemy.orm import Session

from app.adapters.mock_openclaw import MockOpenClawAdapter
from app.core.risk_engine import RiskEngine
from app.core.runtime_monitor import RuntimeMonitor
from app.core.trace_builder import TraceBuilder
from app.models.db_models import ReportDB, RunDB
from app.models.schemas_event import EventCreate
from app.models.schemas_run import RunCreate
from app.services.report_service import ReportService
from app.utils.ids import new_id
from app.utils.time import utc_now


class RunService:
    def __init__(self, db: Session):
        self.db = db

    def create_run(self, payload: RunCreate, workspace_root: str) -> RunDB:
        run = RunDB(
            run_id=new_id("run"),
            task_name=payload.task_name,
            description=payload.description,
            status="running",
            started_at=utc_now(),
            ended_at=None,
            workspace_root=workspace_root,
            actor=payload.actor,
            skill_id=payload.skill_id,
            overall_risk_level="low",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def list_runs(self) -> list[RunDB]:
        return self.db.query(RunDB).order_by(RunDB.started_at.desc()).all()

    def get_run(self, run_id: str) -> RunDB | None:
        return self.db.query(RunDB).filter(RunDB.run_id == run_id).first()

    def finish_run(self, run: RunDB, overall_risk_level: str) -> RunDB:
        run.status = "finished"
        run.ended_at = utc_now()
        run.overall_risk_level = overall_risk_level
        self.db.commit()
        self.db.refresh(run)
        return run

    def execute_scenario(
        self,
        run: RunDB,
        scenario_id: str,
        adapter: MockOpenClawAdapter,
        risk_engine: RiskEngine,
        trace_builder: TraceBuilder,
        report_service: ReportService,
        monitor: RuntimeMonitor,
    ) -> dict:
        if scenario_id == "normal":
            results = adapter.run_normal_task(run.run_id)
        elif scenario_id == "workspace_escape":
            results = adapter.run_workspace_escape_task(run.run_id)
        elif scenario_id == "sensitive_exfiltration":
            results = adapter.run_sensitive_exfiltration_task(run.run_id)
        elif scenario_id == "unauthorized_tool":
            results = adapter.run_unauthorized_tool_task(run.run_id)
        elif scenario_id == "dangerous_command":
            results = adapter.run_dangerous_command_task(run.run_id)
        elif scenario_id == "advanced_intrusion_kill_chain":
            results = adapter.run_advanced_intrusion_kill_chain(run.run_id)
        else:
            results = [{"status": "error", "message": f"unknown scenario: {scenario_id}"}]

        analysis = risk_engine.generate_risk_findings(run.run_id)
        trace = trace_builder.build(run.run_id)

        monitor.record_event(
            event=EventCreate(
                run_id=run.run_id,
                task_id=None,
                event_type="risk_detected",
                action="risk_evaluate",
                resource_type="run",
                resource=run.run_id,
                params_summary=f"scenario={scenario_id}",
                decision="alert" if analysis["findings"] else "allow",
                result_status="ok",
                severity=analysis["overall_risk_level"],
                message=f"Risk findings count={len(analysis['findings'])}",
                trace_id=None,
                metadata={"findings": len(analysis["findings"])},
            )
        )

        report = report_service.generate(
            run_id=run.run_id,
            overall_risk_level=analysis["overall_risk_level"],
            findings=analysis["findings"],
            trace_graph=trace,
        )
        self.finish_run(run, analysis["overall_risk_level"])

        monitor.record_event(
            event=EventCreate(
                run_id=run.run_id,
                task_id=None,
                event_type="report_generated",
                action="report_generate",
                resource_type="report",
                resource=report.report_id,
                params_summary=f"run_id={run.run_id}",
                decision="allow",
                result_status="ok",
                severity="low",
                message="Audit report generated",
                trace_id=None,
                metadata={},
            )
        )

        return {
            "run_id": run.run_id,
            "scenario_id": scenario_id,
            "results": results,
            "analysis": analysis,
            "trace": trace,
            "report_id": report.report_id,
        }

    def get_report_for_run(self, run_id: str) -> ReportDB | None:
        return (
            self.db.query(ReportDB)
            .filter(ReportDB.run_id == run_id)
            .order_by(ReportDB.created_at.desc())
            .first()
        )
