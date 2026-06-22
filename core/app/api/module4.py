from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.dashboard_service import build_dashboard
from app.services.event_detail_service import get_event_detail

router = APIRouter(prefix="/api/module4", tags=["module4"])


@router.get("/dashboard")
def dashboard(time_range: str = Query("7d", pattern="^(today|7d|30d|this_month)$"), db: Session = Depends(get_db)) -> dict:
    return {"success": True, "data": build_dashboard(db, time_range)}


@router.get("/events/{event_id}")
def event_detail(event_id: str, db: Session = Depends(get_db)) -> dict:
    result = get_event_detail(db, event_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Security event not found")
    return result
