from __future__ import annotations

from collections import Counter

from app.schemas.audit import (
    AlignmentReportSummary,
    AuditReportPayload,
    DispositionSummary,
    GoalReportSummary,
    ImpactReportSummary,
    ResourceSummary,
    RiskHitSummary,
    ToolCallSummary,
)
from app.schemas.evidence import RiskFinding
from app.schemas.event import EventSummary
from app.schemas.graph import TimelineItem


class ReportAssembler:
    """Assemble report API payload into a front-end friendly structure."""

    def assemble(
        self,
        run_id: str,
        task_summary: str | None,
        final_risk_level: str | None,
        final_disposition: str | None,
        timeline: list[TimelineItem],
        events: list[EventSummary],
        graph: dict[str, object],
        findings: list[RiskFinding],
        conclusion: str,
        goal_summary: GoalReportSummary | None = None,
    ) -> AuditReportPayload:
        semantic_summary = self._build_semantic_summary(events=events)
        tool_calls = self._build_tool_calls(events=events)
        resources = self._build_resources(events=events)
        risk_hits = self._build_risk_hits(findings=findings)
        disposition_summary = self._build_disposition_summary(events=events)
        alignment_summary = self._build_alignment_summary(events=events)
        impact_summary = self._build_impact_summary(events=events)
        explainability_trace = self._build_explainability_trace(events=events)

        return AuditReportPayload(
            run_id=run_id,
            task_summary=task_summary,
            semantic_summary=semantic_summary,
            tool_calls=tool_calls,
            resources=resources,
            risk_hits=risk_hits,
            timeline=timeline,
            graph=graph,
            final_risk_level=final_risk_level,
            final_disposition=final_disposition,
            disposition_summary=disposition_summary,
            goal_summary=goal_summary or GoalReportSummary(),
            alignment_summary=alignment_summary,
            impact_summary=impact_summary,
            explainability_trace=explainability_trace,
            conclusion=conclusion,
        )

    @staticmethod
    def _build_semantic_summary(events: list[EventSummary]) -> str:
        semantic_events = [item for item in events if item.event_type == "semantic_check_completed"]
        if not semantic_events:
            return "No semantic check events recorded."

        counter = Counter((item.semantic_decision or "unknown").lower() for item in semantic_events)
        parts = [f"{key}:{value}" for key, value in sorted(counter.items())]
        return "; ".join(parts)

    @staticmethod
    def _build_tool_calls(events: list[EventSummary]) -> list[ToolCallSummary]:
        records: list[ToolCallSummary] = []
        for item in events:
            if item.event_type != "tool_call_requested":
                continue
            records.append(
                ToolCallSummary(
                    tool_id=item.tool_id or "unknown_tool",
                    semantic_decision=item.semantic_decision,
                    policy_decision=item.policy_decision,
                    disposition=item.disposition,
                    risk_level=item.risk_level,
                )
            )
        return records

    @staticmethod
    def _build_resources(events: list[EventSummary]) -> list[ResourceSummary]:
        resource_map: dict[tuple[str, str], list[str | None]] = {}
        for item in events:
            if item.event_type != "resource_access_requested":
                continue
            rtype = item.resource_type or "unknown"
            rid = item.resource_id or "unknown"
            key = (rtype, rid)
            bucket = resource_map.setdefault(key, [])
            bucket.append(item.risk_level)

        resources: list[ResourceSummary] = []
        for (rtype, rid), levels in resource_map.items():
            resources.append(
                ResourceSummary(
                    resource_type=rtype,
                    resource_id=rid,
                    access_count=len(levels),
                    max_risk_level=ReportAssembler._max_risk(levels),
                )
            )
        return resources

    @staticmethod
    def _build_risk_hits(findings: list[RiskFinding]) -> list[RiskHitSummary]:
        return [
            RiskHitSummary(
                chain_id=item.chain_id,
                risk_level=item.risk_level,
                explanation=item.reason,
            )
            for item in findings
        ]

    @staticmethod
    def _build_disposition_summary(events: list[EventSummary]) -> DispositionSummary:
        counter = Counter((item.disposition or "").lower() for item in events if item.disposition)
        return DispositionSummary(
            allow=counter.get("allow", 0),
            warn=counter.get("warn", 0),
            deny=counter.get("deny", 0) + counter.get("block", 0),
        )

    @staticmethod
    def _build_alignment_summary(events: list[EventSummary]) -> AlignmentReportSummary:
        alignment_events = [item for item in events if item.event_type == "alignment_evaluation_completed"]
        if not alignment_events:
            return AlignmentReportSummary()
        allowed = [e for e in alignment_events if (e.alignment_decision or "").lower() == "allow"]
        reviewed = [e for e in alignment_events if (e.alignment_decision or "").lower() == "review"]
        denied = [e for e in alignment_events if (e.alignment_decision or "").lower() == "deny"]
        scores = [e.alignment_score for e in alignment_events if e.alignment_score is not None]
        min_score = min(scores) if scores else None
        worst_call = None
        if min_score is not None:
            for e in alignment_events:
                if e.alignment_score == min_score:
                    worst_call = e.tool_call_id
                    break
        return AlignmentReportSummary(
            total_tool_calls=len(alignment_events),
            allowed_count=len(allowed),
            review_count=len(reviewed),
            denied_count=len(denied),
            min_score=min_score,
            worst_call=worst_call,
        )

    @staticmethod
    def _build_impact_summary(events: list[EventSummary]) -> ImpactReportSummary:
        sensitive_access_count = 0
        external_request_count = 0
        high_impact_count = 0
        for item in events:
            if (item.resource_type or "") == "env":
                sensitive_access_count += 1
            if (item.resource_type or "") == "http":
                external_request_count += 1
            if (item.impact_level or "").lower() in {"high", "critical"}:
                high_impact_count += 1
        return ImpactReportSummary(
            sensitive_access_count=sensitive_access_count,
            external_request_count=external_request_count,
            high_impact_count=high_impact_count,
        )

    @staticmethod
    def _build_explainability_trace(events: list[EventSummary]) -> list[dict]:
        trace: list[dict] = []
        for item in events:
            if item.event_type not in {"alignment_evaluation_completed", "alignment_blocked", "tool_call_requested"}:
                continue
            metadata = item.metadata_json or {}
            trace.append(
                {
                    "event_id": item.event_id,
                    "step_id": item.step_id,
                    "tool_id": item.tool_id,
                    "alignment_decision": item.alignment_decision,
                    "alignment_score": item.alignment_score,
                    "intended_effect": item.intended_effect,
                    "impact_level": item.impact_level,
                    "reason": item.alignment_reason,
                    "justification_ref": metadata.get("justification_ref"),
                    "counterfactual_note": metadata.get("counterfactual_note"),
                    "necessity_verdict": metadata.get("necessity_verdict"),
                }
            )
        return trace

    @staticmethod
    def _max_risk(levels: list[str | None]) -> str | None:
        rank = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4,
            "severe": 4,
        }
        selected = None
        selected_rank = 0
        for item in levels:
            normalized = (item or "").lower()
            current = rank.get(normalized, 0)
            if current > selected_rank:
                selected = normalized
                selected_rank = current
        return selected


report_assembler = ReportAssembler()
