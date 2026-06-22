from pathlib import Path

from app.db.models import UploadedDocument
from tests.test_sessions_api import create_session


def test_upload_document(client, db) -> None:
    session_id = create_session(client)
    response = client.post(f"/sessions/{session_id}/docs", files={"file": ("notes.txt", b"password=secret", "text/plain")})
    assert response.status_code == 200
    document = db.get(UploadedDocument, response.json()["document_id"])
    path = Path(__file__).parent.parent / "app" / document.stored_path
    assert path.is_file()
    assert "secret" not in (document.parsed_text_preview or "")
    path.unlink(missing_ok=True)


def test_upload_rejects_missing_session_and_large_file(client) -> None:
    assert client.post("/sessions/missing/docs", files={"file": ("x.txt", b"x", "text/plain")}).status_code == 404
    session_id = create_session(client)
    response = client.post(f"/sessions/{session_id}/docs", files={"file": ("large.bin", b"x" * (10 * 1024 * 1024 + 1), "application/octet-stream")})
    assert response.status_code == 413
