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
from app.services.task_state_service import task_state_service


class TaskStateServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        init_database()

    def test_initialize_and_get_current_step(self) -> None:
        with Session(bind=get_engine()) as db:
            run = run_service.initialize_run(
                db=db,
                session_id="sess_step_1",
                task_summary="step state test",
                task_type="unknown",
            )
            goal = goal_service.create_goal_for_task(
                db=db,
                run_id=run.run_id,
                user_input="请总结 workspace/readme.md",
            )
            step = task_state_service.initialize_first_step(db=db, run_id=run.run_id, goal=goal)
            current = task_state_service.get_current_step(db=db, run_id=run.run_id)
            db.commit()

            self.assertIsNotNone(current)
            assert current is not None
            self.assertEqual(step.step_id, current.step_id)
            self.assertEqual(current.step_index, 1)
            self.assertTrue(current.is_current)
            self.assertIn("file_read", current.allowed_action_types_json)

    def test_transition_after_tool_call_creates_next_step(self) -> None:
        with Session(bind=get_engine()) as db:
            run = run_service.initialize_run(
                db=db,
                session_id="sess_step_2",
                task_summary="step transition test",
                task_type="unknown",
            )
            goal = goal_service.create_goal_for_task(
                db=db,
                run_id=run.run_id,
                user_input="请总结 workspace/readme.md",
            )
            first = task_state_service.initialize_first_step(db=db, run_id=run.run_id, goal=goal)
            completed, next_step = task_state_service.transition_after_tool_call(
                db=db,
                run_id=run.run_id,
                tool_id="workspace_reader",
                final_decision="allow",
                execution_status="mock_completed",
            )
            current = task_state_service.get_current_step(db=db, run_id=run.run_id)
            db.commit()

            self.assertIsNotNone(completed)
            self.assertIsNotNone(next_step)
            assert completed is not None
            assert next_step is not None
            self.assertEqual(completed.step_id, first.step_id)
            self.assertEqual(completed.status, "completed")
            self.assertFalse(completed.is_current)
            self.assertEqual(next_step.step_index, 2)
            self.assertTrue(next_step.is_current)
            self.assertIsNotNone(current)
            assert current is not None
            self.assertEqual(current.step_id, next_step.step_id)

    def test_transition_after_tool_call_blocked_no_change(self) -> None:
        with Session(bind=get_engine()) as db:
            run = run_service.initialize_run(
                db=db,
                session_id="sess_step_3",
                task_summary="step blocked test",
                task_type="unknown",
            )
            goal = goal_service.create_goal_for_task(
                db=db,
                run_id=run.run_id,
                user_input="请总结 workspace/readme.md",
            )
            first = task_state_service.initialize_first_step(db=db, run_id=run.run_id, goal=goal)
            completed, next_step = task_state_service.transition_after_tool_call(
                db=db,
                run_id=run.run_id,
                tool_id="workspace_reader",
                final_decision="deny",
                execution_status="blocked_by_policy_or_semantic_guard",
            )
            current = task_state_service.get_current_step(db=db, run_id=run.run_id)
            db.commit()

            self.assertIsNone(completed)
            self.assertIsNone(next_step)
            self.assertIsNotNone(current)
            assert current is not None
            self.assertEqual(current.step_id, first.step_id)
            self.assertTrue(current.is_current)


if __name__ == "__main__":
    unittest.main()
