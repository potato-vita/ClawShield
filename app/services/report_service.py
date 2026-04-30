from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock

from sqlalchemy.orm import Session

from app.analyzer.evidence_builder import evidence_builder
from app.analyzer.graph_builder import graph_builder
from app.analyzer.risk_analyzer import risk_analyzer
from app.analyzer.timeline_builder import timeline_builder
from app.core.errors import NotFoundError
from app.reports.assembler import report_assembler
from app.repositories.event_repo import event_repository
from app.repositories.run_repo import run_repository
from app.schemas.audit import AuditReportPayload
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _CachedReport:
    marker_event_id: str | None
    generated_at: datetime
    payload: AuditReportPayload


class ReportService:
    """Aggregate run-level report data for API and demo pages."""

    MAX_CACHE_ITEMS = 256

    def __init__(self) -> None:
        self._cache_lock = RLock()
        self._cache: dict[str, _CachedReport] = {}

    def _get_cached_report(self, run_id: str, marker_event_id: str | None) -> AuditReportPayload | None:
        with self._cache_lock:
            cached = self._cache.get(run_id)
            if cached is None:
                return None
            if cached.marker_event_id != marker_event_id:
                return None
            return cached.payload.model_copy(deep=True)

    def _store_cached_report(self, run_id: str, marker_event_id: str | None, payload: AuditReportPayload) -> None:
        with self._cache_lock:
            self._cache[run_id] = _CachedReport(
                marker_event_id=marker_event_id,
                generated_at=datetime.now(timezone.utc),
                payload=payload.model_copy(deep=True),
            )
            if len(self._cache) <= self.MAX_CACHE_ITEMS:
                return

            oldest_key = min(self._cache, key=lambda key: self._cache[key].generated_at)
            self._cache.pop(oldest_key, None)

    def get_report(self, db: Session, run_id: str) -> AuditReportPayload:
        run = run_repository.get_by_run_id(db=db, run_id=run_id)
        if run is None:
            raise NotFoundError(
                message="run not found",
                details={"run_id": run_id},
                error_code="RUN_NOT_FOUND",
            )

        latest_event_id, _ = event_repository.get_latest_marker(db=db, run_id=run_id)
        cached_payload = self._get_cached_report(run_id=run_id, marker_event_id=latest_event_id)
        if cached_payload is not None:
            logger.info("report_service.cache_hit run_id=%s marker=%s", run_id, latest_event_id)
            return cached_payload

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

        payload = report_assembler.assemble(
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
        self._store_cached_report(
            run_id=run_id,
            marker_event_id=latest_event_id,
            payload=payload,
        )
        return payload


report_service = ReportService()
