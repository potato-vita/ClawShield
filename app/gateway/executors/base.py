from __future__ import annotations

from dataclasses import dataclass

from app.gateway.interceptors.base import InterceptedAction


@dataclass
class ExecutorOutput:
    execution_status: str
    output_summary: str
    executor_name: str


class BaseExecutor:
    """Execute normalized action requests with controllable side effects."""

    def execute(self, action: InterceptedAction) -> ExecutorOutput:
        raise NotImplementedError
