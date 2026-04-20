from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.pre_audit import PreAuditEngine
from app.dependencies import get_db
from app.models.db_models import PreAuditResultDB
from app.utils.time import utc_now


router = APIRouter(prefix="/api/preaudit", tags=["preaudit"])


class PreAuditRequest(BaseModel):
    run_id: str
    target_paths: list[str] = Field(default_factory=list)
    skill_source: str | None = None


@router.post("/run")
def run_preaudit(payload: PreAuditRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    root = settings.resolve_path(".")
    expanded = [str((root / p).resolve()) if not Path(p).is_absolute() else p for p in payload.target_paths]

    result = PreAuditEngine().run(target_paths=expanded, skill_source=payload.skill_source)
    record = PreAuditResultDB(
        run_id=payload.run_id,
        target_name=",".join(payload.target_paths),
        target_type="files",
        score=result["pre_audit_score"],
        result_level=result["result_level"],
        findings_json={
            "risk_items": result["risk_items"],
            "suggestions": result["suggestions"],
        },
        created_at=utc_now(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "run_id": payload.run_id,
        "score": record.score,
        "result_level": record.result_level,
        "risk_items": result["risk_items"],
        "suggestions": result["suggestions"],
    }


@router.get("/{run_id}")
def get_preaudit(run_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(PreAuditResultDB)
        .filter(PreAuditResultDB.run_id == run_id)
        .order_by(PreAuditResultDB.created_at.desc())
        .all()
    )
    return rows
