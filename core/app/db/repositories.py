from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AnalysisSession, OpenClawRun


def get_or_create_run(
    db: Session,
    run_id: str,
    session_id: str | None,
    user_goal: str | None = None,
) -> OpenClawRun:
    run = db.get(OpenClawRun, run_id)
    if run is None:
        run = OpenClawRun(
            id=run_id,
            openclaw_session_id=session_id,
            user_goal=user_goal,
            status="running",
        )
        db.add(run)
        db.flush()
    return run


def next_message_index(db: Session, session_id: str) -> int:
    messages = db.scalars(
        select(AnalysisSession).where(AnalysisSession.id == session_id)
    ).all()
    if not messages:
        return 0
    from app.db.models import ChatMessage
    return len(db.scalars(select(ChatMessage).where(ChatMessage.session_id == session_id)).all())
