import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import configure_database
from app.main import app


@pytest.fixture
def client(tmp_path) -> TestClient:
    configure_database(f"sqlite:///{tmp_path / 'test.db'}")
    with TestClient(app) as test_client:
        yield test_client
    from app.db.session import engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db(client):
    from app.db.session import SessionLocal
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
