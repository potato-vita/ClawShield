from pathlib import Path

from sqlalchemy import Engine

from app.db.base import Base
from app.db import session as db_session
from app.db import models as _models  # noqa: F401 - registers ORM metadata


def init_db(target_engine: Engine | None = None) -> None:
    active_engine = target_engine or db_session.engine
    if active_engine.url.get_backend_name() == "sqlite":
        database = active_engine.url.database
        if database and database != ":memory:":
            Path(database).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(active_engine)
