from pathlib import Path

import pytest
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.env_adapter import EnvAdapter
from app.adapters.exec_adapter import ExecAdapter
from app.adapters.file_adapter import FileAdapter
from app.adapters.http_adapter import HttpAdapter
from app.adapters.tool_registry import ToolRegistry
from app.core.boundary_engine import BoundaryEngine
from app.core.gateway import SecurityGateway
from app.core.runtime_monitor import RuntimeMonitor
from app.core.workspace_guard import WorkspaceGuard
from app.models.db_models import Base


@pytest.fixture
def db_session(tmp_path: Path) -> Session:
    db_file = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    with SessionLocal() as db:
        yield db


@pytest.fixture
def gateway_context(tmp_path: Path, db_session: Session) -> dict:
    workspace = tmp_path / "workspace"
    (workspace / "docs").mkdir(parents=True, exist_ok=True)
    (workspace / "output").mkdir(parents=True, exist_ok=True)
    (workspace / "docs" / "brief.txt").write_text("hello clawshield", encoding="utf-8")
    (workspace / ".env").write_text("SECRET_TOKEN=abc", encoding="utf-8")

    rules = {
        "workspace": {
            "root": str(workspace),
            "deny_outside": True,
            "sensitive_patterns": [".env", "*secret*"],
            "blocked_paths": ["/etc"],
        },
        "capability": {
            "allow_network": True,
            "allowed_domains": ["example-safe.local"],
            "allowed_tools": ["summarize_tool", "search_tool"],
            "blocked_commands": ["rm -rf /"],
        },
        "trust": {
            "allowed_skill_sources": ["local_verified", "official_repo"],
            "default_skill_trust": "unknown",
            "tool_trust": {"summarize_tool": "trusted"},
        },
    }
    rules_file = tmp_path / "boundary_rules.yaml"
    rules_file.write_text(yaml.safe_dump(rules, allow_unicode=True, sort_keys=False), encoding="utf-8")

    boundary = BoundaryEngine(str(rules_file))
    guard = WorkspaceGuard(str(workspace), sensitive_patterns=boundary.sensitive_patterns)
    monitor = RuntimeMonitor(db=db_session, log_file=str(tmp_path / "runtime.log"))

    gateway = SecurityGateway(
        boundary_engine=boundary,
        runtime_monitor=monitor,
        file_adapter=FileAdapter(workspace_guard=guard),
        http_adapter=HttpAdapter(),
        exec_adapter=ExecAdapter(),
        env_adapter=EnvAdapter(),
        tool_registry=ToolRegistry(),
    )
    return {
        "workspace": workspace,
        "rules_file": rules_file,
        "gateway": gateway,
        "monitor": monitor,
        "boundary": boundary,
    }
