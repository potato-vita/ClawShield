from datetime import datetime, timedelta, timezone

from app.db.models import SecurityEvent


def add_event(db, event_id: str, risk: str, score: float, department: str, username: str, days_ago: int = 0) -> None:
    db.add(SecurityEvent(
        id=event_id, event_title=event_id, event_type="test", risk_level=risk, risk_score=score,
        department_name=department, username=username, process_name="openclaw",
        occurred_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    ))
    db.commit()


def test_empty_dashboard(client) -> None:
    data = client.get("/api/module4/dashboard?time_range=7d").json()["data"]
    assert data["summary"]["total_alerts"] == 0
    assert data["risk_trend"] == []
    assert data["high_risk_events"] == []


def test_dashboard_aggregates_real_events(client, db) -> None:
    add_event(db, "event_dash_1", "critical", 95, "研发部", "alice")
    add_event(db, "event_dash_2", "high", 80, "研发部", "bob")
    add_event(db, "event_dash_3", "medium", 50, "销售部", "amy")
    data = client.get("/api/module4/dashboard?time_range=7d").json()["data"]
    assert data["summary"]["total_alerts"] == 3
    assert data["summary"]["critical_count"] == 1
    assert data["summary"]["high_risk_count"] == 2
    assert data["risk_trend"][0]["alert_count"] == 3
    assert data["top_departments"][0]["department_name"] == "研发部"
    assert len(data["high_risk_events"]) == 2


def test_dashboard_time_ranges(client, db) -> None:
    add_event(db, "event_today", "high", 80, "研发部", "alice")
    add_event(db, "event_old", "critical", 95, "研发部", "alice", days_ago=20)
    assert client.get("/api/module4/dashboard?time_range=today").json()["data"]["summary"]["total_alerts"] == 1
    assert client.get("/api/module4/dashboard?time_range=30d").json()["data"]["summary"]["total_alerts"] == 2
    assert client.get("/api/module4/dashboard?time_range=this_month").status_code == 200
