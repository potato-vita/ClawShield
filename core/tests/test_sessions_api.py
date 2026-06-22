from sqlalchemy import func, select

from app.db.models import AnalysisSession, ChatMessage, SecurityEvent


def create_session(client) -> str:
    return client.post("/sessions", json={"title": "新分析会话"}).json()["id"]


def test_session_create_list_render_chat_and_delete(client, db) -> None:
    session_id = create_session(client)
    assert any(item["id"] == session_id for item in client.get("/sessions").json())
    db.add(SecurityEvent(
        id="event_chat", event_title="敏感文件访问", event_type="sensitive_file_access",
        risk_level="critical", risk_score=95,
    ))
    db.commit()
    response = client.post(f"/sessions/{session_id}/chat", json={"message": "最近 7 天有哪些高风险事件？"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event_chat" in response.text
    assert db.scalar(select(func.count()).select_from(ChatMessage).where(ChatMessage.session_id == session_id)) == 2
    assert "event_chat" in client.get(f"/sessions/{session_id}/render").text
    assert client.delete(f"/sessions/{session_id}").json()["success"] is True
    assert db.get(AnalysisSession, session_id).status == "deleted"


def test_abort_marks_session(client, db) -> None:
    session_id = create_session(client)
    assert client.post(f"/sessions/{session_id}/abort", json={"reason": "stop"}).status_code == 200
    assert db.get(AnalysisSession, session_id).status == "aborted"


def test_eino_can_append_exact_session_messages(client, db) -> None:
    session_id = create_session(client)
    response = client.post(
        f"/sessions/{session_id}/messages",
        json={"role": "assistant", "content": "Eino analysis", "related_event_id": "event_123"},
    )
    assert response.status_code == 200
    message = db.scalar(
        select(ChatMessage).where(ChatMessage.session_id == session_id, ChatMessage.role == "assistant")
    )
    assert message.content == "Eino analysis"
    assert message.related_event_id == "event_123"
