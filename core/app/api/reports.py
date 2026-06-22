from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.reports import ReportCreate
from app.services.report_service import generate_report

router = APIRouter(prefix="/api/module4", tags=["reports"])
EXPORT_DIR = Path(__file__).resolve().parent.parent / "data" / "exports"


@router.post("/reports")
def create_report(request: ReportCreate, db: Session = Depends(get_db)) -> dict:
    report = generate_report(db, request.title, request.time_range, request.session_id)
    filename = Path(report.content_html_path or "").name
    return {"success": True, "report_id": report.id, "download_url": f"/api/module4/exports/{filename}"}


@router.get("/exports/{filename}")
def export_report(filename: str) -> FileResponse:
    safe_name = Path(filename).name
    path = EXPORT_DIR / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Export not found")
    return FileResponse(path, media_type="text/html", filename=safe_name)
