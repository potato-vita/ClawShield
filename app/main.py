from pathlib import Path

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.routes_demo import router as demo_router
from app.api.routes_preaudit import router as preaudit_router
from app.api.routes_reports import router as reports_router
from app.api.routes_rules import router as rules_router
from app.api.routes_runs import router as runs_router
from app.api.routes_tasks import router as tasks_router
from app.config import PROJECT_ROOT, get_settings
from app.dependencies import SessionLocal, get_db, init_db
from app.models.db_models import EventDB
from app.models.schemas_run import RunCreate, ScenarioExecuteRequest
from app.services.demo_service import DemoService
from app.services.report_service import ReportService
from app.services.rule_service import RuleService
from app.services.run_service import RunService
from app.services.task_service import TaskService


settings = get_settings()
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "app" / "templates"))


def ensure_seed_files() -> None:
    workspace = settings.resolve_path(settings.workspace_root)
    (workspace / "docs").mkdir(parents=True, exist_ok=True)
    (workspace / "output").mkdir(parents=True, exist_ok=True)

    brief = workspace / "docs" / "brief.txt"
    if not brief.exists():
        brief.write_text(
            "ClawShield demo brief: show secure tool orchestration with runtime monitoring.",
            encoding="utf-8",
        )

    env_file = workspace / ".env"
    if not env_file.exists():
        env_file.write_text("DEMO_TOKEN=clawshield-demo-token\n", encoding="utf-8")


app = FastAPI(title=settings.app_name, version=settings.version)
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "app" / "static")), name="static")

app.include_router(runs_router)
app.include_router(rules_router)
app.include_router(reports_router)
app.include_router(tasks_router)
app.include_router(demo_router)
app.include_router(preaudit_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    ensure_seed_files()
    with SessionLocal() as db:
        RuleService(db).seed_from_risk_yaml(str(settings.resolve_path(settings.risk_rules_path)))


@app.get("/")
def dashboard(request: Request, db: Session = Depends(get_db)):
    summary = TaskService(db).dashboard_summary()
    recent_runs = RunService(db).list_runs()[:8]
    scenarios = DemoService().list_scenarios()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "summary": summary,
            "runs": recent_runs,
            "scenarios": scenarios,
            "app_name": settings.app_name,
        },
    )


@app.get("/runs")
def runs_page(request: Request, db: Session = Depends(get_db)):
    runs = RunService(db).list_runs()
    return templates.TemplateResponse(request, "runs.html", {"runs": runs})


@app.get("/runs/{run_id}")
def run_detail_page(run_id: str, request: Request, db: Session = Depends(get_db)):
    run = RunService(db).get_run(run_id)
    events = (
        db.query(EventDB)
        .filter(EventDB.run_id == run_id)
        .order_by(EventDB.created_at.asc())
        .all()
    )
    trace = RunService(db).get_report_for_run(run_id)
    trace_graph = trace.trace_graph_json if trace else {"nodes": [], "edges": [], "risk_paths": []}
    return templates.TemplateResponse(
        request,
        "run_detail.html",
        {
            "run": run,
            "events": events,
            "trace_graph": trace_graph,
        },
    )


@app.get("/rules")
def rules_page(request: Request, db: Session = Depends(get_db)):
    rules = RuleService(db).list_rules()
    boundaries = settings.resolve_path(settings.rules_path).read_text(encoding="utf-8")
    return templates.TemplateResponse(
        request,
        "rules.html",
        {
            "rules": rules,
            "boundaries": boundaries,
        },
    )


@app.get("/reports/{run_id}")
def report_detail_page(run_id: str, request: Request, db: Session = Depends(get_db)):
    report = ReportService(db, export_dir=str(settings.resolve_path(settings.report_export_dir))).get_by_run(run_id)
    return templates.TemplateResponse(request, "report_detail.html", {"report": report, "run_id": run_id})


@app.get("/preaudit")
def preaudit_page(request: Request):
    return templates.TemplateResponse(request, "preaudit.html", {"result": None})


@app.post("/preaudit")
def preaudit_submit(
    request: Request,
    run_id: str = Form(...),
    target_paths: str = Form(...),
    skill_source: str = Form("unknown"),
    db: Session = Depends(get_db),
):
    from app.core.pre_audit import PreAuditEngine

    path_list = [x.strip() for x in target_paths.splitlines() if x.strip()]
    root = settings.resolve_path(".")
    expanded = [str((root / p).resolve()) if not Path(p).is_absolute() else p for p in path_list]
    result = PreAuditEngine().run(expanded, skill_source)
    return templates.TemplateResponse(
        request,
        "preaudit.html",
        {
            "result": result,
            "run_id": run_id,
            "target_paths": target_paths,
            "skill_source": skill_source,
        },
    )


@app.get("/demo")
def demo_page(request: Request):
    scenarios = DemoService().list_scenarios()
    return templates.TemplateResponse(request, "demo_scenarios.html", {"scenarios": scenarios})


@app.post("/demo/run")
def demo_run(scenario_id: str = Form(...), db: Session = Depends(get_db)):
    run_service = RunService(db)
    run = run_service.create_run(
        RunCreate(task_name=f"demo_{scenario_id}", description=f"Run demo scenario: {scenario_id}"),
        workspace_root=str(settings.resolve_path(settings.workspace_root)),
    )

    from app.api.routes_runs import _build_runtime

    runtime = _build_runtime(db)
    run_service_rt, monitor, risk_engine, trace_builder, adapter, report_service = runtime
    run_service_rt.execute_scenario(
        run=run,
        scenario_id=scenario_id,
        adapter=adapter,
        risk_engine=risk_engine,
        trace_builder=trace_builder,
        report_service=report_service,
        monitor=monitor,
    )

    return RedirectResponse(url=f"/runs/{run.run_id}", status_code=303)


@app.post("/runs/new")
def create_and_execute_run(
    task_name: str = Form(...),
    scenario_id: str = Form(...),
    db: Session = Depends(get_db),
):
    run_service = RunService(db)
    run = run_service.create_run(
        RunCreate(task_name=task_name, description=f"UI run with scenario {scenario_id}"),
        workspace_root=str(settings.resolve_path(settings.workspace_root)),
    )

    from app.api.routes_runs import _build_runtime

    run_service_rt, monitor, risk_engine, trace_builder, adapter, report_service = _build_runtime(db)
    run_service_rt.execute_scenario(
        run=run,
        scenario_id=ScenarioExecuteRequest(scenario_id=scenario_id).scenario_id,
        adapter=adapter,
        risk_engine=risk_engine,
        trace_builder=trace_builder,
        report_service=report_service,
        monitor=monitor,
    )
    return RedirectResponse(url=f"/runs/{run.run_id}", status_code=303)
