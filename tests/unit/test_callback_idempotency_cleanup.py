from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.callback_idempotency_service import CallbackIdempotencyService
from app.settings import get_settings


class _FakeRepository:
    def __init__(self, deleted_count: int = 2) -> None:
        self.deleted_count = deleted_count
        self.calls = 0

    def delete_older_than(self, db, *, cutoff):  # noqa: ANN001
        del db, cutoff
        self.calls += 1
        return self.deleted_count


class CallbackIdempotencyCleanupTestCase(unittest.TestCase):
    def test_periodic_cleanup_respects_interval(self) -> None:
        repo = _FakeRepository(deleted_count=3)
        service = CallbackIdempotencyService(repository=repo)  # type: ignore[arg-type]
        settings = get_settings()
        old_values = (
            settings.callback_delivery_cleanup_interval_seconds,
            settings.callback_delivery_retention_days,
        )
        settings.callback_delivery_cleanup_interval_seconds = 120
        settings.callback_delivery_retention_days = 10
        try:
            first = service.periodic_cleanup(db=None)  # type: ignore[arg-type]
            second = service.periodic_cleanup(db=None)  # type: ignore[arg-type]
        finally:
            (
                settings.callback_delivery_cleanup_interval_seconds,
                settings.callback_delivery_retention_days,
            ) = old_values
        self.assertEqual(first, 3)
        self.assertEqual(second, 0)
        self.assertEqual(repo.calls, 1)


if __name__ == "__main__":
    unittest.main()
