from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session

from app.db import get_engine, init_database
from app.schemas.tool_call import ActionType
from app.services.alignment_service import alignment_service
from app.services.goal_service import goal_service
from app.services.run_service import run_service


class AlignmentServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        init_database()

    def test_summary_goal_denies_external_upload(self) -> None:
        with Session(bind=get_engine()) as db:
            run = run_service.initialize_run(
                db=db,
                session_id="sess_align_1",
                task_summary="align test",
                task_type="unknown",
            )
            goal_service.create_goal_for_task(db=db, run_id=run.run_id, user_input="请总结 workspace/report.md")

            result = alignment_service.evaluate(
                db=db,
                run_id=run.run_id,
                tool_id="http_fetcher",
                action_type="http",
                arguments={"method": "POST", "url": "https://example.com/upload", "data": "x"},
                model_reason="发送处理结果",
                raw_context={},
            )
            db.commit()

            self.assertEqual(result.alignment_decision, "deny")
            self.assertEqual(result.intended_effect, "external_upload")
            self.assertLess(result.alignment_score, 0.35)

    def test_summary_goal_allows_workspace_read(self) -> None:
        with Session(bind=get_engine()) as db:
            run = run_service.initialize_run(
                db=db,
                session_id="sess_align_2",
                task_summary="align test",
                task_type="unknown",
            )
            goal_service.create_goal_for_task(db=db, run_id=run.run_id, user_input="请总结 workspace/report.md")

            action_type: ActionType = "file_read"
            result = alignment_service.evaluate(
                db=db,
                run_id=run.run_id,
                tool_id="workspace_reader",
                action_type=action_type,
                arguments={"file_path": "./workspace/report.md"},
                model_reason="需要读取文件进行总结",
                raw_context={},
            )
            db.commit()

            self.assertEqual(result.alignment_decision, "allow")
            self.assertEqual(result.intended_effect, "workspace_read")
            self.assertGreaterEqual(result.alignment_score, 0.7)


if __name__ == "__main__":
    unittest.main()
