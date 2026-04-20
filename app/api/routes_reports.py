from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.report_service import ReportService
from app.config import get_settings


router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{run_id}")
def get_report(run_id: str, db: Session = Depends(get_db)):
    settings = get_settings()
    report = ReportService(db=db, export_dir=str(settings.resolve_path(settings.report_export_dir))).get_by_run(run_id)
    if not report:
        raise HTTPException(status_code=404, detail="report not found")
    return report
