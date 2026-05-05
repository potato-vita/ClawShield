from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError, RuntimePipelineError
from app.demo.scenarios import (
    RISK_FREE_INPUT_EXAMPLES,
    SAFE_FREE_INPUT_EXAMPLES,
    get_standard_scenario,
    list_standard_scenarios,
)
from app.schemas.task import TaskIngestRequest
from app.schemas.tool_call import ToolCallRequest
from app.services.bridge_service import BridgeService, bridge_service
from app.services.report_service import ReportService, report_service
from app.services.task_service import TaskService, task_service

logger = logging.getLogger(__name__)


class DemoService:
    """Round-10 demo orchestration for standard scenarios and fallback prompts."""

    def __init__(
        self,
        task_service_instance: TaskService,
        bridge_service_instance: BridgeService,
        report_service_instance: ReportService,
    ) -> None:
        self._task_service = task_service_instance
        self._bridge_service = bridge_service_instance
        self._report_service = report_service_instance

    @staticmethod
    def list_standard_scenarios() -> list[dict[str, str]]:
        return [
            {
                "scenario_id": scenario.scenario_id,
                "name": scenario.name,
                "prompt": scenario.prompt,
                "expected_chain": scenario.expected_chain,
            }
            for scenario in list_standard_scenarios()
        ]

    @staticmethod
    def free_input_examples() -> dict[str, list[str]]:
        return {
            "safe_tasks": list(SAFE_FREE_INPUT_EXAMPLES),
            "risk_tasks": list(RISK_FREE_INPUT_EXAMPLES),
        }

    def run_standard_scenario(self, db: Session, scenario_id: str) -> dict:
        scenario = get_standard_scenario(scenario_id)
        if scenario is None:
            raise NotFoundError(
                message="standard scenario not found",
                details={"scenario_id": scenario_id},
                error_code="SCENARIO_NOT_FOUND",
            )

        logger.info("demo_service.run_scenario.start scenario_id=%s", scenario_id)
        try:
            ingest_result = self._task_service.ingest_task(
                db=db,
                payload=TaskIngestRequest(
                    session_id=scenario.session_id,
                    user_input=scenario.prompt,
                    source="demo",
                    metadata={"scenario_id": scenario.scenario_id, "standard_case": True},
                ),
            )
            run_id = ingest_result.run_id

            tool_results: list[dict] = []
            for index, call in enumerate(scenario.calls, start=1):
                tool_result = self._bridge_service.process_tool_call(
                    db=db,
                    payload=ToolCallRequest(
                        run_id=run_id,
                        tool_call_id=f"{call.tool_call_id}_{index}",
                        tool_id=call.tool_id,
                        arguments=call.arguments,
                    ),
                )
                tool_results.append(
                    {
                        "tool_call_id": tool_result["tool_call_id"],
                        "tool_id": call.tool_id,
                        "decision": tool_result["decision"],
                        "risk_level": tool_result["risk_level"],
                        "execution_status": tool_result["execution_status"],
                    }
                )

            report = self._report_service.get_report(db=db, run_id=run_id)
        except AppError:
            raise
        except Exception as exc:
            raise RuntimePipelineError(
                message="failed to execute standard demo scenario",
                error_code="DEMO_SCENARIO_RUN_FAILED",
                details={"scenario_id": scenario_id, "reason": str(exc)},
            ) from exc

        logger.info(
            "demo_service.run_scenario.done scenario_id=%s run_id=%s final_risk=%s",
            scenario_id,
            run_id,
            report.final_risk_level,
        )
        return {
            "scenario": {
                "scenario_id": scenario.scenario_id,
                "name": scenario.name,
                "expected_chain": scenario.expected_chain,
            },
            "run_id": run_id,
            "run_detail_url": f"/api/v1/ui/runs/{run_id}",
            "report_url": f"/api/v1/ui/runs/{run_id}/report",
            "final_risk_level": report.final_risk_level,
            "final_disposition": report.final_disposition,
            "tool_results": tool_results,
        }


demo_service = DemoService(
    task_service_instance=task_service,
    bridge_service_instance=bridge_service,
    report_service_instance=report_service,
)
