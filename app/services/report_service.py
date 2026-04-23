from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.analyzer.evidence_builder import evidence_builder
from app.analyzer.graph_builder import graph_builder
from app.analyzer.risk_analyzer import risk_analyzer
from app.analyzer.timeline_builder import timeline_builder
from app.core.errors import NotFoundError
from app.reports.assembler import report_assembler
from app.repositories.run_repo import run_repository
from app.schemas.audit import AuditReportPayload
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)


class ReportService:
    """Aggregate run-level report data for API and demo pages."""

    def get_report(self, db: Session, run_id: str) -> AuditReportPayload:
        run = run_repository.get_by_run_id(db=db, run_id=run_id)
        if run is None:
            raise NotFoundError(
                message="run not found",
                details={"run_id": run_id},
                error_code="RUN_NOT_FOUND",
            )

        logger.info("report_service.start run_id=%s", run_id)

        events = audit_service.list_events(
            db=db,
            run_id=run_id,
            limit=1000,
            offset=0,
            order="asc",
        )
        timeline = timeline_builder.build(db=db, run_id=run_id)
        nodes, edges = evidence_builder.build(db=db, run_id=run_id)
        analysis = risk_analyzer.analyze(db=db, run_id=run_id)
        findings = analysis["findings"]

        graph = graph_builder.build(
            run_id=run_id,
            nodes=nodes,
            edges=edges,
            findings=findings,
        )

        run_repository.update_risk_conclusion(
            db=db,
            run_id=run_id,
            final_risk_level=analysis["final_risk_level"],
            disposition=analysis["final_disposition"],
        )

        logger.info(
            "report_service.done run_id=%s events=%s timeline=%s findings=%s",
            run_id,
            len(events),
            len(timeline),
            len(findings),
        )

        return report_assembler.assemble(
            run_id=run_id,
            task_summary=run.task_summary,
            timeline=timeline,
            events=events,
            graph=graph,
            findings=findings,
            final_risk_level=analysis["final_risk_level"],
            final_disposition=analysis["final_disposition"],
            conclusion=analysis["summary"],
        )


report_service = ReportService()
