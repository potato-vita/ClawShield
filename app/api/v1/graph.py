from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analyzer.evidence_builder import evidence_builder
from app.analyzer.graph_builder import graph_builder
from app.analyzer.risk_analyzer import risk_analyzer
from app.analyzer.timeline_builder import timeline_builder
from app.core.errors import AppError, NotFoundError, RuntimePipelineError
from app.db import get_db
from app.repositories.run_repo import run_repository
from app.schemas.common import APIResponse, success_response
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs")


@router.get("/{run_id}/timeline", response_model=APIResponse)
def get_timeline(run_id: str, db: Session = Depends(get_db)) -> APIResponse:
    run = run_repository.get_by_run_id(db=db, run_id=run_id)
    if run is None:
        raise NotFoundError(
            message="run not found",
            details={"run_id": run_id},
            error_code="RUN_NOT_FOUND",
        )

    timeline = timeline_builder.build(db=db, run_id=run_id)
    return success_response(
        data={
            "run_id": run_id,
            "timeline": [item.model_dump() for item in timeline],
        }
    )


@router.get("/{run_id}/graph", response_model=APIResponse)
def get_graph(run_id: str, db: Session = Depends(get_db)) -> APIResponse:
    run = run_repository.get_by_run_id(db=db, run_id=run_id)
    if run is None:
        raise NotFoundError(
            message="run not found",
            details={"run_id": run_id},
            error_code="RUN_NOT_FOUND",
        )

    try:
        logger.info("graph.build.start run_id=%s", run_id)
        nodes, edges = evidence_builder.build(db=db, run_id=run_id)
        analysis = risk_analyzer.analyze(db=db, run_id=run_id)
        findings = analysis["findings"]

        graph_payload = graph_builder.build(
            run_id=run_id,
            nodes=nodes,
            edges=edges,
            findings=findings,
        )

        for finding in findings:
            audit_service.record_event(
                db=db,
                run_id=run_id,
                session_id=run.session_id,
                event_type="risk_chain_formed",
                event_stage="risk_chain",
                actor_type="system",
                tool_id=None,
                resource_type="risk_chain",
                resource_id=finding.chain_id,
                input_summary=finding.name,
                output_summary=finding.reason,
                risk_level=finding.risk_level,
                disposition=finding.disposition,
                status="recorded",
            )

        audit_service.record_event(
            db=db,
            run_id=run_id,
            session_id=run.session_id,
            event_type="final_risk_conclusion_generated",
            event_stage="risk_chain",
            actor_type="system",
            risk_level=analysis["final_risk_level"],
            disposition=analysis["final_disposition"],
            output_summary=analysis["summary"],
            status="recorded",
        )

        run_repository.update_risk_conclusion(
            db=db,
            run_id=run_id,
            final_risk_level=analysis["final_risk_level"],
            disposition=analysis["final_disposition"],
        )
        db.commit()
        logger.info(
            "graph.build.done run_id=%s nodes=%s edges=%s findings=%s",
            run_id,
            len(graph_payload["nodes"]),
            len(graph_payload["edges"]),
            len(findings),
        )
    except AppError:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise RuntimePipelineError(
            message=f"graph building failed: {exc}",
            error_code="GRAPH_BUILD_FAILED",
            details={"run_id": run_id},
        ) from exc

    return success_response(data=graph_payload)
