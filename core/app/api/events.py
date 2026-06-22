from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.plugin import EventBatchRequest, EventBatchResponse
from app.services.event_ingest import ingest_events

router = APIRouter(tags=["plugin"])


@router.post("/v1/events/batch", response_model=EventBatchResponse)
def event_batch(request: EventBatchRequest, db: Session = Depends(get_db)) -> EventBatchResponse:
    return ingest_events(db, request.events)
