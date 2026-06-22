from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ChatMessage, Report, SecurityEvent


def range_start(time_range: str, now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    if time_range == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if time_range == "30d":
        return now - timedelta(days=30)
    if time_range == "this_month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return now - timedelta(days=7)


def build_dashboard(db: Session, time_range: str = "7d") -> dict:
    start = range_start(time_range)
    events = db.scalars(
        select(SecurityEvent).where(SecurityEvent.occurred_at >= start).order_by(SecurityEvent.occurred_at.desc())
    ).all()
    reports = db.scalars(select(Report).order_by(Report.created_at.desc())).all()
    query_count = len(db.scalars(select(ChatMessage).where(ChatMessage.role == "user", ChatMessage.created_at >= start)).all())

    daily = Counter(event.occurred_at.date().isoformat() for event in events)
    channel_count = Counter(event.process_name or event.target_type or "unknown" for event in events)
    department_events: dict[str, list[SecurityEvent]] = defaultdict(list)
    user_events: dict[tuple[str, str], list[SecurityEvent]] = defaultdict(list)
    for event in events:
        department_events[event.department_name or "未分配"].append(event)
        user_events[(event.username or "unknown", event.department_name or "未分配")].append(event)

    total = len(events)
    return {
        "summary": {
            "total_alerts": total,
            "critical_count": sum(event.risk_level == "critical" for event in events),
            "high_risk_count": sum(event.risk_level in {"high", "critical"} for event in events),
            "query_count": query_count,
            "start_time": start.isoformat(),
            "latest_report_id": reports[0].id if reports else None,
        },
        "risk_trend": [{"bucket": day, "alert_count": count} for day, count in sorted(daily.items())],
        "channels": [
            {"channel": name, "alert_count": count, "percent": round(count * 100 / total, 1) if total else 0}
            for name, count in channel_count.most_common(8)
        ],
        "top_departments": [
            {
                "department_name": name,
                "alert_count": len(items),
                "high_risk_count": sum(item.risk_level == "high" for item in items),
                "critical_count": sum(item.risk_level == "critical" for item in items),
                "risk_score_avg": round(mean(item.risk_score for item in items), 1),
            }
            for name, items in sorted(department_events.items(), key=lambda pair: len(pair[1]), reverse=True)[:8]
        ],
        "top_users": [
            {
                "username": key[0], "department_name": key[1], "alert_count": len(items),
                "risk_score_avg": round(mean(item.risk_score for item in items), 1),
            }
            for key, items in sorted(user_events.items(), key=lambda pair: len(pair[1]), reverse=True)[:8]
        ],
        "high_risk_events": [
            {
                "event_id": event.id,
                "risk_level": event.risk_level,
                "username": event.username,
                "department_name": event.department_name,
                "file_name": event.file_name,
                "event_title": event.event_title,
                "timestamp": event.occurred_at.isoformat(),
            }
            for event in events if event.risk_level in {"high", "critical"}
        ][:20],
    }
