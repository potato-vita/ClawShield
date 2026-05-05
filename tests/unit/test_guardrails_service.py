from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session

from app.core.ids import generate_task_id
from app.db import get_engine, init_database
from app.models.task import Task
from app.repositories.task_repo import task_repository
from app.schemas.tool_call import ToolCallRequest
from app.services.guardrails_service import guardrails_service
from app.services.run_service import run_service


class GuardrailsServiceTestCase(unittest.TestCase):
    def test_evaluate_tool_call_with_mocked_semantic_backend(self) -> None:
        init_database()
        with Session(bind=get_engine()) as db:
            run = run_service.initialize_run(
                db=db,
                session_id="unit_guardrails_session",
                task_summary="请分析这个项目",
                task_type="unknown",
            )
            task_repository.create(
                db=db,
                task=Task(
                    task_id=generate_task_id(),
                    run_id=run.run_id,
                    user_input="请分析这个项目",
                    source="unit-test",
                ),
            )
            db.commit()

            payload = ToolCallRequest(
                run_id=run.run_id,
                tool_call_id="unit_tc_guardrails",
                tool_id="workspace_reader",
                arguments={"file_path": "./workspace/demo.txt"},
            )

            with patch(
                "app.services.guardrails_service.evaluate_candidate_action",
                return_value={"semantic_decision": "warn", "semantic_reason": "mocked semantic decision"},
            ):
                decision = guardrails_service.evaluate_tool_call(db=db, payload=payload)

            self.assertEqual(decision.decision, "warn")
            self.assertEqual(decision.task_type, "analysis")
            self.assertIn("mocked semantic decision", decision.semantic_reason)


if __name__ == "__main__":
    unittest.main()
