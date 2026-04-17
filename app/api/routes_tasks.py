from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.task_service import TaskService


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    return TaskService(db).dashboard_summary()
