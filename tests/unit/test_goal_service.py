from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session

from app.db import get_engine, init_database
from app.schemas.task import TaskIngestRequest
from app.services.audit_service import audit_service
from app.services.goal_service import goal_service
from app.services.run_service import run_service
from app.services.task_service import task_service


class GoalServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        init_database()

    def test_summary_task_builds_goal_contract(self) -> None:
        with Session(bind=get_engine()) as db:
            run = run_service.initialize_run(
                db=db,
                session_id="sess_goal_summary",
                task_summary="summary goal test",
                task_type="unknown",
            )
            goal = goal_service.create_goal_for_task(
                db=db,
                run_id=run.run_id,
                user_input="请总结 workspace/report.md",
            )
            db.commit()

            self.assertIn(goal.task_intent, {"summary", "analysis"})
            self.assertIn("file_read", goal.allowed_action_types_json)
            self.assertIn("external_upload", goal.forbidden_effects_json)
            self.assertIn("shell_exec", goal.forbidden_effects_json)

    def test_external_invoke_task_builds_goal_contract(self) -> None:
        with Session(bind=get_engine()) as db:
            run = run_service.initialize_run(
                db=db,
                session_id="sess_goal_http",
                task_summary="external invoke goal test",
                task_type="unknown",
            )
            goal = goal_service.create_goal_for_task(
                db=db,
                run_id=run.run_id,
                user_input="帮我调用接口查询天气",
            )
            db.commit()

            self.assertEqual(goal.task_intent, "external_invoke")
            self.assertIn("http", goal.allowed_action_types_json)

    def test_task_ingest_records_goal_event_and_returns_goal_fields(self) -> None:
        with Session(bind=get_engine()) as db:
            resp = task_service.ingest_task(
                db=db,
                payload=TaskIngestRequest(
                    session_id="sess_goal_ingest",
                    user_input="请总结 workspace/report.md",
                    source="unit",
                    metadata={},
                ),
            )

            self.assertTrue(resp.goal_id.startswith("goal_"))
            self.assertIn(resp.task_intent, {"summary", "analysis"})
            self.assertIn("file_read", resp.allowed_action_types)

            events = audit_service.list_events(db=db, run_id=resp.run_id, limit=200, offset=0, order="asc")
            event_types = {item.event_type for item in events}
            self.assertIn("goal_contract_created", event_types)
            self.assertIn("task_step_initialized", event_types)


if __name__ == "__main__":
    unittest.main()
