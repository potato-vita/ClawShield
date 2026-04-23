from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.settings import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return

    db_path = database_url.replace("sqlite:///", "", 1)
    if db_path == ":memory:":
        return

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


def init_engine() -> Engine:
    global _engine, _session_factory
    if _engine is not None and _session_factory is not None:
        return _engine

    settings = get_settings()
    _ensure_sqlite_parent(settings.database_url)

    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    _engine = create_engine(settings.database_url, future=True, connect_args=connect_args)
    _session_factory = sessionmaker(
        bind=_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )
    return _engine


def get_engine() -> Engine:
    return init_engine()


def get_db() -> Generator[Session, None, None]:
    global _session_factory
    if _session_factory is None:
        init_engine()

    assert _session_factory is not None
    db = _session_factory()
    try:
        yield db
    finally:
        db.close()


def init_database() -> None:
    # Import side effects register all ORM models with Base.metadata.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
