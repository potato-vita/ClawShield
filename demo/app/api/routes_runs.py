from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.adapters.env_adapter import EnvAdapter
from app.adapters.exec_adapter import ExecAdapter
from app.adapters.file_adapter import FileAdapter
from app.adapters.http_adapter import HttpAdapter
from app.adapters.mock_openclaw import MockOpenClawAdapter
from app.adapters.tool_registry import ToolRegistry
from app.config import get_settings
from app.core.boundary_engine import BoundaryEngine
from app.core.gateway import SecurityGateway
from app.core.risk_engine import RiskEngine
from app.core.runtime_monitor import RuntimeMonitor
from app.core.trace_builder import TraceBuilder
from app.core.workspace_guard import WorkspaceGuard
from app.dependencies import get_db
from app.models.db_models import EventDB
from app.models.schemas_event import EventRead
from app.models.schemas_run import RunCreate, RunRead, ScenarioExecuteRequest
from app.services.report_service import ReportService
from app.services.run_service import RunService


router = APIRouter(prefix="/api/runs", tags=["runs"])


def _build_runtime(db: Session) -> tuple[RunService, RuntimeMonitor, RiskEngine, TraceBuilder, MockOpenClawAdapter, ReportService]:
    settings = get_settings()
    boundary = BoundaryEngine(str(settings.resolve_path(settings.rules_path)))
    workspace_root = settings.resolve_path(boundary.workspace_root)
    guard = WorkspaceGuard(str(workspace_root), sensitive_patterns=boundary.sensitive_patterns)

    monitor = RuntimeMonitor(db=db, log_file=str(settings.resolve_path(settings.log_file)))
    gateway = SecurityGateway(
        boundary_engine=boundary,
        runtime_monitor=monitor,
        file_adapter=FileAdapter(workspace_guard=guard),
        http_adapter=HttpAdapter(),
        exec_adapter=ExecAdapter(),
        env_adapter=EnvAdapter(),
        tool_registry=ToolRegistry(),
    )
    adapter = MockOpenClawAdapter(gateway=gateway)
    risk_engine = RiskEngine(db=db, risk_rules_path=str(settings.resolve_path(settings.risk_rules_path)))
    trace_builder = TraceBuilder(db=db)
    report_service = ReportService(db=db, export_dir=str(settings.resolve_path(settings.report_export_dir)))
    run_service = RunService(db=db)
    return run_service, monitor, risk_engine, trace_builder, adapter, report_service


@router.post("/start", response_model=RunRead)
def start_run(payload: RunCreate, db: Session = Depends(get_db)):
    settings = get_settings()
    boundary = BoundaryEngine(str(settings.resolve_path(settings.rules_path)))
    workspace_root = str(settings.resolve_path(boundary.workspace_root))
    run = RunService(db).create_run(payload=payload, workspace_root=workspace_root)
    return run


@router.post("/{run_id}/execute-scenario")
def execute_scenario(run_id: str, payload: ScenarioExecuteRequest, db: Session = Depends(get_db)):
    run_service, monitor, risk_engine, trace_builder, adapter, report_service = _build_runtime(db)
    run = run_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    result = run_service.execute_scenario(
        run=run,
        scenario_id=payload.scenario_id,
        adapter=adapter,
        risk_engine=risk_engine,
        trace_builder=trace_builder,
        report_service=report_service,
        monitor=monitor,
    )
    return result


@router.get("", response_model=list[RunRead])
def list_runs(db: Session = Depends(get_db)):
    return RunService(db).list_runs()


@router.get("/{run_id}", response_model=RunRead)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = RunService(db).get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.get("/{run_id}/events", response_model=list[EventRead])
def get_run_events(run_id: str, db: Session = Depends(get_db)):
    events = (
        db.query(EventDB)
        .filter(EventDB.run_id == run_id)
        .order_by(EventDB.created_at.asc())
        .all()
    )
    return events


@router.get("/{run_id}/trace")
def get_run_trace(run_id: str, db: Session = Depends(get_db)):
    return TraceBuilder(db).build(run_id)


@router.get("/{run_id}/report")
def get_run_report(run_id: str, db: Session = Depends(get_db)):
    report = RunService(db).get_report_for_run(run_id)
    if not report:
        raise HTTPException(status_code=404, detail="report not found")
    return report
