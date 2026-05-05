from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.settings import _load_yaml_config, _normalize_database_url, _resolve_project_path


class ConfigLoadingTestCase(unittest.TestCase):
    def test_yaml_config_is_loadable(self) -> None:
        config_path = _resolve_project_path("configs/app.yaml")
        loaded = _load_yaml_config(str(config_path))
        self.assertIn("app_name", loaded)
        self.assertIn("database_url", loaded)

    def test_relative_sqlite_url_is_normalized_to_absolute_path(self) -> None:
        normalized = _normalize_database_url("sqlite:///./data/unit_test.db")
        self.assertTrue(normalized.startswith("sqlite:///"))
        self.assertIn("data/unit_test.db", normalized)


if __name__ == "__main__":
    unittest.main()
