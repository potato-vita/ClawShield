from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.gateway.interceptors.file_read_interceptor import FileReadInterceptor
from app.gateway.path_utils import normalize_file_resource_id
from app.schemas.tool_call import ActionRequest


class PathNormalizationTestCase(unittest.TestCase):
    def test_normalize_workspace_relative_path(self) -> None:
        normalized = normalize_file_resource_id("workspace/../workspace/report.md")
        self.assertEqual(normalized, "./workspace/report.md")

    def test_normalize_absolute_workspace_path(self) -> None:
        abs_path = str((PROJECT_ROOT / "workspace" / "report.md").resolve(strict=False))
        normalized = normalize_file_resource_id(abs_path)
        self.assertEqual(normalized, "./workspace/report.md")

    def test_interceptor_uses_normalized_resource_id(self) -> None:
        request = ActionRequest(
            run_id="run_test",
            tool_call_id="tc_test",
            tool_id="workspace_reader",
            action_type="file_read",
            arguments={"file_path": "workspace/../workspace/a.txt"},
            task_type="analysis",
            semantic_decision="allow",
            semantic_reason="test",
        )
        intercepted = FileReadInterceptor().intercept(request)
        self.assertEqual(intercepted.resource_type, "file")
        self.assertEqual(intercepted.resource_id, "./workspace/a.txt")


if __name__ == "__main__":
    unittest.main()
