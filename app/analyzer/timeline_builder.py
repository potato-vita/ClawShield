from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.graph import TimelineItem
from app.services.audit_service import audit_service


class TimelineBuilder:
    """Build ordered run-level timeline entries from normalized audit events."""

    _title_map = {
        "task_received": "Task Received",
        "task_classified": "Task Classified",
        "dialog_state_changed": "Dialog State Updated",
        "chat_message_received": "Chat Message Received",
        "tool_call_requested": "Tool Call Requested",
        "semantic_check_completed": "Semantic Check Completed",
        "policy_check_completed": "Policy Check Completed",
        "resource_access_requested": "Resource Access Requested",
        "tool_execution_started": "Tool Execution Started",
        "tool_execution_completed": "Tool Execution Completed",
        "tool_result_received": "Tool Result Received",
        "disposition_applied": "Disposition Applied",
        "risk_rule_matched": "Risk Rule Matched",
    }

    def build(self, db: Session, run_id: str) -> list[TimelineItem]:
        events = audit_service.list_events(
            db=db,
            run_id=run_id,
            limit=500,
            offset=0,
            order="asc",
        )

        timeline: list[TimelineItem] = []
        for event in events:
            title = self._title_map.get(event.event_type, event.event_type.replace("_", " ").title())
            summary_parts: list[str] = []

            if event.tool_id:
                summary_parts.append(f"tool={event.tool_id}")
            if event.resource_type or event.resource_id:
                summary_parts.append(f"resource={event.resource_type}:{event.resource_id}")
            if event.semantic_decision:
                summary_parts.append(f"semantic={event.semantic_decision}")
            if event.policy_decision:
                summary_parts.append(f"policy={event.policy_decision}")
            if event.status:
                summary_parts.append(f"status={event.status}")

            timeline.append(
                TimelineItem(
                    ts=event.ts,
                    title=title,
                    summary="; ".join(summary_parts) if summary_parts else "event recorded",
                    event_type=event.event_type,
                    risk_level=event.risk_level,
                    disposition=event.disposition,
                    related_ids=[
                        value
                        for value in [event.event_id, event.tool_id, event.resource_id]
                        if value
                    ],
                )
            )

        return timeline


timeline_builder = TimelineBuilder()
