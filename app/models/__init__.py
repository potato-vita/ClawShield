"""Import ORM models so metadata registration is explicit."""

from app.models.audit_event import AuditEvent
from app.models.audit_report import AuditReport
from app.models.alignment_evaluation import AlignmentEvaluation
from app.models.evidence_edge import EvidenceEdge
from app.models.risk_hit import RiskHit
from app.models.run import Run
from app.models.task import Task
from app.models.task_goal import TaskGoal
from app.models.task_step import TaskStep

__all__ = [
    "Run",
    "Task",
    "AuditEvent",
    "RiskHit",
    "EvidenceEdge",
    "AuditReport",
    "TaskGoal",
    "TaskStep",
    "AlignmentEvaluation",
]
