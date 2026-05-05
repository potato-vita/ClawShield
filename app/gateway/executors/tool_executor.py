from __future__ import annotations

from app.gateway.executors.base import BaseExecutor, ExecutorOutput
from app.gateway.interceptors.base import InterceptedAction


class ToolExecutor(BaseExecutor):
    def execute(self, action: InterceptedAction) -> ExecutorOutput:
        return ExecutorOutput(
            execution_status="mock_completed",
            output_summary=f"mock tool execution for {action.request.tool_id}",
            executor_name="tool_executor",
        )
