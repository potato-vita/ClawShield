from pathlib import Path

from app.db.models import Report, SecurityEvent
from tests.test_sessions_api import create_session


def test_report_generation_download_and_chat_link(client, db) -> None:
    db.add(SecurityEvent(id="event_report", event_title="报告事件", event_type="test", risk_level="critical", risk_score=95))
    db.commit()
    response = client.post("/api/module4/reports", json={"title": "周报", "time_range": "7d"})
    assert response.status_code == 200
    data = response.json()
    report = db.get(Report, data["report_id"])
    path = Path(__file__).parent.parent / "app" / "data" / (report.content_html_path or "")
    assert path.is_file()
    download = client.get(data["download_url"])
    assert download.status_code == 200
    assert "周报" in download.text
    session_id = create_session(client)
    chat = client.post(f"/sessions/{session_id}/chat", json={"message": "请生成报告"})
    assert "/api/module4/exports/" in chat.text
    path.unlink(missing_ok=True)
    for extra in path.parent.glob("report_*.html"):
        extra.unlink(missing_ok=True)
