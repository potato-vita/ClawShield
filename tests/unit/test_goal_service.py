from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session

from app.db import get_engine, init_database
from app.services.goal_service import goal_service
from app.services.run_service import run_service


class GoalServiceTestCase(unittest.TestCase):
    def test_create_goal_for_summary_task(self) -> None:
        init_database()
        with Session(bind=get_engine()) as db:
            run = run_service.initialize_run(
                db=db,
                session_id="goal_summary_session",
                task_summary="请总结 workspace/report.md",
                task_type="unknown",
            )
            goal = goal_service.create_goal_for_task(
                db=db,
                run_id=run.run_id,
                user_input="请总结 workspace/report.md",
                task_type="unknown",
                metadata={"source": "unit"},
            )
            db.commit()

            self.assertTrue(goal.goal_id.startswith("goal_"))
            self.assertEqual(goal.task_intent, "summary")
            self.assertIn("file_read", goal.allowed_action_types_json)
            self.assertIn("external_upload", goal.forbidden_effects_json)

    def test_create_goal_for_external_invoke_task(self) -> None:
        init_database()
        with Session(bind=get_engine()) as db:
            run = run_service.initialize_run(
                db=db,
                session_id="goal_http_session",
                task_summary="帮我调用接口查询天气",
                task_type="unknown",
            )
            goal = goal_service.create_goal_for_task(
                db=db,
                run_id=run.run_id,
                user_input="帮我调用接口查询天气",
                task_type="unknown",
            )
            db.commit()

            self.assertEqual(goal.task_intent, "external_invoke")
            self.assertIn("http", goal.allowed_action_types_json)


if __name__ == "__main__":
    unittest.main()
