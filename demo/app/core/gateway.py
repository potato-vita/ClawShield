from __future__ import annotations

from app.adapters.env_adapter import EnvAdapter
from app.adapters.exec_adapter import ExecAdapter
from app.adapters.file_adapter import FileAdapter
from app.adapters.http_adapter import HttpAdapter
from app.adapters.tool_registry import ToolRegistry
from app.core.boundary_engine import BoundaryEngine
from app.core.runtime_monitor import RuntimeMonitor
from app.models.gateway_models import ExecutionContext, GatewayResponse
from app.models.schemas_event import EventCreate
from app.utils.enums import GatewayStatus


class SecurityGateway:
    def __init__(
        self,
        boundary_engine: BoundaryEngine,
        runtime_monitor: RuntimeMonitor,
        file_adapter: FileAdapter,
        http_adapter: HttpAdapter,
        exec_adapter: ExecAdapter,
        env_adapter: EnvAdapter,
        tool_registry: ToolRegistry,
    ):
        self.boundary = boundary_engine
        self.monitor = runtime_monitor
        self.file_adapter = file_adapter
        self.http_adapter = http_adapter
        self.exec_adapter = exec_adapter
        self.env_adapter = env_adapter
        self.tool_registry = tool_registry

    def _record_precheck(
        self,
        ctx: ExecutionContext,
        action: str,
        resource_type: str,
        resource: str,
        decision: str,
        severity: str,
        message: str,
        tags: list[str] | None = None,
    ) -> str:
        event = self.monitor.record_event(
            EventCreate(
                run_id=ctx.run_id,
                task_id=ctx.task_id,
                event_type=f"{action}_attempt",
                action=action,
                resource_type=resource_type,
                resource=resource,
                params_summary="pre-check",
                decision=decision,
                result_status="checked",
                severity=severity,
                message=message,
                trace_id=ctx.trace_id,
                metadata={
                    "skill_id": ctx.skill_id,
                    "tool_id": ctx.tool_id,
                    "tags": tags or [],
                    "sensitive": "sensitive" in (tags or []),
                },
            )
        )
        return event.event_id

    def _record_result(
        self,
        ctx: ExecutionContext,
        parent_event_id: str,
        action: str,
        resource_type: str,
        resource: str,
        decision: str,
        result_status: str,
        severity: str,
        message: str,
        tags: list[str] | None = None,
    ) -> str:
        event = self.monitor.record_event(
            EventCreate(
                run_id=ctx.run_id,
                task_id=ctx.task_id,
                parent_event_id=parent_event_id,
                event_type="action_completed" if result_status == "ok" else "action_blocked",
                action=action,
                resource_type=resource_type,
                resource=resource,
                params_summary="execution-result",
                decision=decision,
                result_status=result_status,
                severity=severity,
                message=message,
                trace_id=ctx.trace_id,
                metadata={
                    "skill_id": ctx.skill_id,
                    "tool_id": ctx.tool_id,
                    "tags": tags or [],
                    "sensitive": "sensitive" in (tags or []),
                },
            )
        )
        return event.event_id

    def _build_response(
        self,
        decision: str,
        message: str,
        result: dict,
        event_ids: list[str],
    ) -> GatewayResponse:
        if decision == "allow":
            status = GatewayStatus.ALLOWED.value
        elif decision == "alert":
            status = GatewayStatus.ALERTED.value
        elif decision == "block":
            status = GatewayStatus.BLOCKED.value
        else:
            status = GatewayStatus.ERROR.value
        return GatewayResponse(status=status, message=message, decision=decision, result=result, event_ids=event_ids)

    def read_file(self, ctx: ExecutionContext, path: str) -> GatewayResponse:
        bd = self.boundary.check_file_access(path=path, action="read")
        pre_id = self._record_precheck(
            ctx,
            action="file_read",
            resource_type="file",
            resource=path,
            decision=bd.decision,
            severity=bd.severity,
            message=bd.message,
            tags=bd.tags,
        )
        if bd.decision == "block":
            end_id = self._record_result(
                ctx,
                pre_id,
                action="file_read",
                resource_type="file",
                resource=path,
                decision=bd.decision,
                result_status="blocked",
                severity=bd.severity,
                message=bd.message,
                tags=bd.tags,
            )
            return self._build_response(bd.decision, bd.message, {}, [pre_id, end_id])

        content = self.file_adapter.read(path)
        end_id = self._record_result(
            ctx,
            pre_id,
            action="file_read",
            resource_type="file",
            resource=path,
            decision=bd.decision,
            result_status="ok",
            severity=bd.severity,
            message="File read completed",
            tags=bd.tags,
        )
        return self._build_response(bd.decision, bd.message, {"content": content}, [pre_id, end_id])

    def write_file(self, ctx: ExecutionContext, path: str, content: str) -> GatewayResponse:
        bd = self.boundary.check_file_access(path=path, action="write")
        pre_id = self._record_precheck(
            ctx,
            action="file_write",
            resource_type="file",
            resource=path,
            decision=bd.decision,
            severity=bd.severity,
            message=bd.message,
            tags=bd.tags,
        )
        if bd.decision == "block":
            end_id = self._record_result(
                ctx,
                pre_id,
                action="file_write",
                resource_type="file",
                resource=path,
                decision=bd.decision,
                result_status="blocked",
                severity=bd.severity,
                message=bd.message,
                tags=bd.tags,
            )
            return self._build_response(bd.decision, bd.message, {}, [pre_id, end_id])

        written = self.file_adapter.write(path, content)
        end_id = self._record_result(
            ctx,
            pre_id,
            action="file_write",
            resource_type="file",
            resource=path,
            decision=bd.decision,
            result_status="ok",
            severity=bd.severity,
            message="File write completed",
            tags=bd.tags,
        )
        return self._build_response(
            bd.decision,
            bd.message,
            {"written": written, "size": len(content.encode("utf-8"))},
            [pre_id, end_id],
        )

    def invoke_tool(self, ctx: ExecutionContext, tool_id: str, payload: dict) -> GatewayResponse:
        trust = self.boundary.check_trust(skill_source=ctx.metadata.get("skill_source"), tool_id=tool_id)
        bd = self.boundary.check_tool_invocation(tool_id=tool_id)
        decision = bd.decision
        if trust.decision == "alert" and bd.decision == "allow":
            decision = "alert"

        tags = (bd.tags or []) + (trust.tags or [])
        message = f"{bd.message}; {trust.message}"
        pre_id = self._record_precheck(
            ctx,
            action="tool_invoke",
            resource_type="tool",
            resource=tool_id,
            decision=decision,
            severity=max(bd.severity, trust.severity, key=lambda x: ["low", "medium", "high", "critical"].index(x)),
            message=message,
            tags=tags,
        )
        if bd.decision == "block":
            end_id = self._record_result(
                ctx,
                pre_id,
                action="tool_invoke",
                resource_type="tool",
                resource=tool_id,
                decision=bd.decision,
                result_status="blocked",
                severity=bd.severity,
                message=bd.message,
                tags=tags,
            )
            return self._build_response(bd.decision, bd.message, {}, [pre_id, end_id])

        result = self.tool_registry.invoke(tool_id=tool_id, payload=payload)
        end_id = self._record_result(
            ctx,
            pre_id,
            action="tool_invoke",
            resource_type="tool",
            resource=tool_id,
            decision=decision,
            result_status="ok",
            severity="medium" if decision == "alert" else "low",
            message="Tool invocation completed",
            tags=tags,
        )
        return self._build_response(decision, message, result, [pre_id, end_id])

    def http_request(self, ctx: ExecutionContext, method: str, url: str, payload: dict | None = None) -> GatewayResponse:
        bd = self.boundary.check_http_request(url=url)
        pre_id = self._record_precheck(
            ctx,
            action="http_request",
            resource_type="url",
            resource=url,
            decision=bd.decision,
            severity=bd.severity,
            message=bd.message,
            tags=bd.tags,
        )
        if bd.decision == "block":
            end_id = self._record_result(
                ctx,
                pre_id,
                action="http_request",
                resource_type="url",
                resource=url,
                decision=bd.decision,
                result_status="blocked",
                severity=bd.severity,
                message=bd.message,
                tags=bd.tags,
            )
            return self._build_response(bd.decision, bd.message, {}, [pre_id, end_id])

        result = self.http_adapter.request(method=method, url=url, payload=payload)
        end_id = self._record_result(
            ctx,
            pre_id,
            action="http_request",
            resource_type="url",
            resource=url,
            decision=bd.decision,
            result_status="ok",
            severity=bd.severity,
            message="HTTP request simulated",
            tags=bd.tags,
        )
        return self._build_response(bd.decision, bd.message, result, [pre_id, end_id])

    def exec_command(self, ctx: ExecutionContext, command: str, cwd: str | None = None) -> GatewayResponse:
        bd = self.boundary.check_command_execution(command=command)
        pre_id = self._record_precheck(
            ctx,
            action="command_exec",
            resource_type="command",
            resource=command,
            decision=bd.decision,
            severity=bd.severity,
            message=bd.message,
            tags=bd.tags,
        )
        if bd.decision == "block":
            end_id = self._record_result(
                ctx,
                pre_id,
                action="command_exec",
                resource_type="command",
                resource=command,
                decision=bd.decision,
                result_status="blocked",
                severity=bd.severity,
                message=bd.message,
                tags=bd.tags,
            )
            return self._build_response(bd.decision, bd.message, {}, [pre_id, end_id])

        result = self.exec_adapter.exec(command=command, cwd=cwd)
        end_id = self._record_result(
            ctx,
            pre_id,
            action="command_exec",
            resource_type="command",
            resource=command,
            decision=bd.decision,
            result_status="ok",
            severity=bd.severity,
            message="Command executed in controlled mode",
            tags=bd.tags,
        )
        return self._build_response(bd.decision, bd.message, result, [pre_id, end_id])

    def read_env(self, ctx: ExecutionContext, key: str) -> GatewayResponse:
        bd = self.boundary.check_env_read(key=key)
        pre_id = self._record_precheck(
            ctx,
            action="env_read",
            resource_type="env",
            resource=key,
            decision=bd.decision,
            severity=bd.severity,
            message=bd.message,
            tags=bd.tags,
        )
        if bd.decision == "block":
            end_id = self._record_result(
                ctx,
                pre_id,
                action="env_read",
                resource_type="env",
                resource=key,
                decision=bd.decision,
                result_status="blocked",
                severity=bd.severity,
                message=bd.message,
                tags=bd.tags,
            )
            return self._build_response(bd.decision, bd.message, {}, [pre_id, end_id])

        value = self.env_adapter.read(key=key)
        end_id = self._record_result(
            ctx,
            pre_id,
            action="env_read",
            resource_type="env",
            resource=key,
            decision=bd.decision,
            result_status="ok",
            severity=bd.severity,
            message="Env read completed",
            tags=bd.tags,
        )
        return self._build_response(bd.decision, bd.message, {"key": key, "value": value}, [pre_id, end_id])
