from __future__ import annotations

from app.gateway.executors.base import BaseExecutor, ExecutorOutput
from app.gateway.interceptors.base import InterceptedAction


class HttpExecutor(BaseExecutor):
    def execute(self, action: InterceptedAction) -> ExecutorOutput:
        return ExecutorOutput(
            execution_status="mock_completed",
            output_summary=f"mock http request to {action.resource_id}",
            executor_name="http_executor",
        )
