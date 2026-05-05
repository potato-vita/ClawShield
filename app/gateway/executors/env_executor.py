from __future__ import annotations

from app.gateway.executors.base import BaseExecutor, ExecutorOutput
from app.gateway.interceptors.base import InterceptedAction


class EnvExecutor(BaseExecutor):
    def execute(self, action: InterceptedAction) -> ExecutorOutput:
        return ExecutorOutput(
            execution_status="mock_completed",
            output_summary=f"mock env read for {action.resource_id}",
            executor_name="env_executor",
        )
