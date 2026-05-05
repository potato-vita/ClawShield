from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


def main() -> None:
    session_id = "oc_session_verify_001"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/bridge/opencaw/callback/message",
            json={
                "session_id": session_id,
                "messages": [
                    {"role": "user", "content": "请帮我验证 callback 是否落库"},
                    {"role": "assistant", "content": "好的，开始验证"},
                ],
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success"):
            raise RuntimeError(f"callback API returned failure: {payload}")
        run_id = str(payload.get("data", {}).get("run_id", ""))

    db_path = PROJECT_ROOT / "data" / "clawshield.db"
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            """
            select event_type, actor_type, run_id
            from audit_events
            where run_id = ?
            order by id desc
            limit 10
            """,
            (run_id,),
        ).fetchall()
        chat_count = con.execute(
            """
            select count(*)
            from audit_events
            where run_id = ? and event_type = 'chat_message_received'
            """,
            (run_id,),
        ).fetchone()[0]
    finally:
        con.close()

    print(f"run_id={run_id}")
    print(f"chat_message_received_count={chat_count}")
    print("latest_run_events=")
    for event_type, actor_type, row_run_id in rows:
        print(f"- {event_type} actor={actor_type} run_id={row_run_id}")

    if chat_count < 2:
        raise RuntimeError("callback verification failed: chat_message_received count is lower than expected")

    print("callback_verification=ok")


if __name__ == "__main__":
    main()

