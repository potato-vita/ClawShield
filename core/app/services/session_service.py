import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AnalysisSession, ChatMessage, SecurityEvent
from app.services.idgen import new_id


def add_message(
    db: Session,
    session_id: str,
    role: str,
    content: str,
    related_event_id: str | None = None,
    related_report_id: str | None = None,
) -> ChatMessage:
    index = db.scalar(select(func.count()).select_from(ChatMessage).where(ChatMessage.session_id == session_id)) or 0
    message = ChatMessage(
        id=new_id("message"), session_id=session_id, role=role, content=content,
        order_index=index, related_event_id=related_event_id, related_report_id=related_report_id,
    )
    db.add(message)
    session = db.get(AnalysisSession, session_id)
    if session:
        session.updated_at = datetime.now(timezone.utc)
        session.last_message_at = datetime.now(timezone.utc)
        if role == "user" and session.title == "新分析会话":
            session.title = content[:40]
    return message


def build_analysis_answer(db: Session, message: str) -> tuple[str, list[str]]:
    events = db.scalars(
        select(SecurityEvent)
        .where(SecurityEvent.risk_level.in_(["high", "critical"]))
        .order_by(SecurityEvent.occurred_at.desc())
        .limit(8)
    ).all()
    ids = [event.id for event in events]
    if not events:
        return "当前数据库中没有高危或 Critical 安全事件。可以先通过 OpenClaw 插件触发一次审计。", []
    lines = [
        f"最近记录到 {len(events)} 条高危事件：",
        *[f"- {event.id}｜{event.risk_level.upper()}｜{event.event_title}｜{event.occurred_at.isoformat()}" for event in events],
        "以上事件均来自 TraceShield Core 数据库。点击事件 ID 可在右侧查看工具调用、审计证据和风险链路。",
    ]
    if "部门" in message:
        lines.append("可在仪表盘的 Top 部门区域查看聚合分布。")
    return "\n".join(lines), ids


def sse_payload(answer: str, event_ids: list[str], download_url: str | None = None) -> str:
    messages = [
        {"beginRendering": {"root": "root"}},
        {"surfaceUpdate": {"surfaceId": "root", "components": [
            {"id": "answer", "component": {"Text": {"text": answer}}}
        ]}},
        {"text": answer, "event_ids": event_ids, "download_url": download_url},
    ]
    return "".join(f"data: {json.dumps(item, ensure_ascii=False)}\n\n" for item in messages)
