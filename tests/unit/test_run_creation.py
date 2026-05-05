from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session

from app.db import get_engine, init_database
from app.repositories.run_repo import run_repository
from app.services.run_service import run_service


class RunCreationTestCase(unittest.TestCase):
    def test_initialize_run_persists_run_with_default_status(self) -> None:
        init_database()
        with Session(bind=get_engine()) as db:
            run = run_service.initialize_run(
                db=db,
                session_id="unit_run_session",
                task_summary="unit test run creation",
                task_type="analysis",
            )
            db.commit()

            persisted = run_repository.get_by_run_id(db=db, run_id=run.run_id)
            self.assertIsNotNone(persisted)
            assert persisted is not None
            self.assertTrue(persisted.run_id.startswith("run_"))
            self.assertEqual(persisted.status, "created")
            self.assertEqual(persisted.task_type, "analysis")


if __name__ == "__main__":
    unittest.main()
