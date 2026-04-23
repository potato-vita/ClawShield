from __future__ import annotations

from app.gateway.executors.base import BaseExecutor, ExecutorOutput
from app.gateway.interceptors.base import InterceptedAction


class FileExecutor(BaseExecutor):
    def execute(self, action: InterceptedAction) -> ExecutorOutput:
        return ExecutorOutput(
            execution_status="mock_completed",
            output_summary=f"mock file read from {action.resource_id}",
            executor_name="file_executor",
        )
