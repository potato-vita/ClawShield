from __future__ import annotations

import sys
import unittest
from pathlib import Path

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db import get_engine, init_database
from app.services.run_service import run_service
from app.services.task_state_service import task_state_service


class TaskStateServiceTestCase(unittest.TestCase):
    def test_create_initial_step_and_transition(self) -> None:
        try:
            init_database()
        except OperationalError as exc:
            if "already exists" not in str(exc):
                raise
        with Session(bind=get_engine()) as db:
            run = run_service.initialize_run(
                db=db,
                session_id="step_unit_session",
                task_summary="step state test",
                task_type="analysis",
            )
            first = task_state_service.create_initial_step(
                db=db,
                run_id=run.run_id,
                goal_id="goal_unit",
                task_intent="analysis",
                allowed_action_types=["file_read"],
            )
            transitioned = task_state_service.transition_step(
                db=db,
                run_id=run.run_id,
                target_state="tool_planning",
                reason="unit_test",
            )
            db.commit()

            self.assertEqual(first.state, "analyzing")
            self.assertEqual(first.status, "completed")
            self.assertEqual(transitioned.state, "tool_planning")
            self.assertEqual(transitioned.status, "active")
            self.assertEqual(transitioned.parent_step_id, first.step_id)


if __name__ == "__main__":
    unittest.main()
